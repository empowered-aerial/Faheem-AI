import copy
import inspect
import re
import unicodedata
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from faheem_location import analyze_location, confirm_location, find_areas
from faheem_report import generate_civic_report, format_report_ar

SESSIONS = {}


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=5000)


def normalize_result(result):
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif hasattr(result, "dict"):
        result = result.dict()

    if not isinstance(result, dict):
        raise ValueError("The analysis function must return a dictionary.")

    return result


def normalize_confirmation_text(text):
    value = unicodedata.normalize("NFKC", str(text or "")).lower()
    value = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", value)

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ؤ": "و",
        "ئ": "ي",
        "ى": "ي",
        "ک": "ك",
        "ی": "ي",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def is_confirmation(text):
    value = normalize_confirmation_text(text)

    if any(value.startswith(item) for item in (
        "نعم لكن",
        "نعم ولكن",
        "نعم الموقع خطا",
        "نعم غير الموقع",
        "نعم غير صحيح",
    )):
        return False

    accepted = {
        "نعم",
        "نعم اوكد",
        "نعم اوكد الموقع",
        "نعم اوكد ذلك",
        "اوكد",
        "اوكد الموقع",
        "اوكد ذلك",
        "اكد",
        "اكد الموقع",
        "صحيح",
        "صحيح الموقع",
        "الموقع صحيح",
        "تمام",
        "موافق",
        "اي",
        "اي نعم",
        "اكيد",
        "بالتاكيد",
    }

    return value in accepted


def is_rejection(text):
    value = normalize_confirmation_text(text)

    rejected = {
        "لا",
        "لا غير صحيح",
        "غير صحيح",
        "الموقع خطا",
        "الموقع غير صحيح",
        "ليس صحيحا",
        "مو صحيح",
        "غلط",
        "الموقع غلط",
    }

    return value in rejected


def append_text(original, addition):
    original = (original or "").strip()
    addition = (addition or "").strip()

    if not addition:
        return original

    if not original:
        return addition

    return original + "\n" + addition


def extract_duration(text):
    value = normalize_confirmation_text(text)

    patterns = [
        (r"منذ\s+(?:ثلاثة|ثلاثه|3|٣)\s+ايام", "for three days"),
        (r"منذ\s+(?:يومين|يومان|2|٢)", "for two days"),
        (r"منذ\s+(?:يوم|يوما|1|١)", "for one day"),
        (r"منذ\s+(?:اسبوعين|اسبوعان|اسبوعان)", "for two weeks"),
        (r"منذ\s+(?:اسبوع|اسبوعا)", "for a week"),
        (r"منذ\s+(?:امس)", "since yesterday"),
        (r"منذ\s+(?:اليوم)", "since today"),
        (r"منذ\s+(?:الصباح|الصبح)", "since this morning"),
        (r"من\s+(?:ثلاثة|ثلاثه|3|٣)\s+ايام", "for three days"),
        (r"من\s+(?:يومين|يومان|2|٢)", "for two days"),
        (r"من\s+(?:اسبوع)", "for a week"),
        (r"من\s+(?:امس)", "since yesterday"),
    ]

    for pattern, duration in patterns:
        match = re.search(pattern, value)

        if match:
            return duration, match.group(0)

    return None, None


def apply_duration_to_analysis(analysis, text):
    duration, matched_text = extract_duration(text)

    if not duration:
        return analysis

    extraction = analysis.setdefault("extraction", {})
    if not isinstance(extraction, dict):
        extraction = {}
        analysis["extraction"] = extraction

    extraction["duration"] = duration

    entities = extraction.setdefault("entities", [])
    if not isinstance(entities, list):
        entities = []
        extraction["entities"] = entities

    entities[:] = [
        item for item in entities
        if not (
            isinstance(item, dict)
            and (item.get("label") or item.get("type")) == "DURATION"
        )
    ]

    entities.append({
        "label": "DURATION",
        "type": "DURATION",
        "span_text": matched_text,
        "normalized_value": duration,
        "assertion": "explicit",
    })

    return analysis


def create_chat_router(analyze_text):
    if not callable(analyze_text):
        raise TypeError("analyze_text must be a callable function.")

    router = APIRouter()

    async def run_analysis(text, context=""):
        result = analyze_text(text, context=context) if context else analyze_text(text)

        if inspect.isawaitable(result):
            result = await result

        return normalize_result(result)

    def full_context(state):
        return "\n".join(
            item for item in [
                state.get("complaint_text", ""),
                state.get("supplemental_text", ""),
            ]
            if item
        )

    async def refresh_analysis(state):
        state["analysis"] = await run_analysis(
            state["complaint_text"],
            state.get("supplemental_text", ""),
        )

        apply_duration_to_analysis(
            state["analysis"],
            full_context(state),
        )

    def refresh_location(state, source_text=None, preferred_area=None):
        text = source_text or state.get("location_text", "")

        state["location"] = analyze_location(
            text,
            state["analysis"],
            preferred_area=preferred_area,
            context_text=full_context(state),
        )

        return state["location"]

    def response(session_id, state, reply, report=None):
        report = report if report is not None else state.get("report")

        return {
            "session_id": session_id,
            "reply_ar": reply,
            "report": report,
            "report_ar": format_report_ar(report) if report else None,
            "report_ready": bool(
                report and report.get("ready_for_review")
            ),
            "awaiting_confirmation": state["stage"] == "awaiting_confirmation",
            "awaiting_area": state["stage"] == "awaiting_area",
            "awaiting_review": state["stage"] == "awaiting_review",
            "stage": state["stage"],
            "analysis": state["analysis"],
            "location": state["location"],
        }

    async def start_case(session_id, message):
        analysis = await run_analysis(message)
        apply_duration_to_analysis(analysis, message)

        location = analyze_location(
            message,
            analysis,
            context_text=message,
        )

        state = {
            "complaint_text": message,
            "supplemental_text": "",
            "location_text": message,
            "analysis": analysis,
            "location": location,
            "report": None,
            "stage": (
                "awaiting_confirmation"
                if location.get("area")
                else "awaiting_area"
            ),
        }

        SESSIONS[session_id] = state
        return state

    def update_confirmed_analysis(state, location, report):
        analysis = copy.deepcopy(state["analysis"])

        extraction = analysis.setdefault("extraction", {})
        if not isinstance(extraction, dict):
            extraction = {}
            analysis["extraction"] = extraction

        extraction_location = extraction.setdefault("location", {})

        landmarks_ar = location.get("landmarks_ar") or []
        directions = location.get("direction_cues") or []

        extraction_location.update({
            "area_ar_candidate": location.get("area_ar"),
            "area_en_candidate": location.get("area"),
            "landmark_candidate": landmarks_ar[0] if landmarks_ar else None,
            "directional_cue": directions[0] if directions else None,
            "coordinates": location.get("coordinates"),
            "resolution_status": "confirmed",
            "verification_status": "user_confirmed",
            "user_confirmed": True,
        })

        completion = analysis.setdefault("completion", {})
        completion.update({
            "missing_fields": report.get("missing_fields", []),
            "needs_clarification": not report.get("ready_for_review", False),
            "next_action": (
                "report_ready"
                if report.get("ready_for_review")
                else "ask_for_missing_fields"
            ),
            "clarification_question_ar": None,
        })

        return analysis

    def build_report(session_id, state):
        report = generate_civic_report(
            complaint_text=state["complaint_text"],
            analysis=state["analysis"],
            location=state["location"],
            user_confirmed=True,
        )

        state["report"] = report

        state["analysis"] = update_confirmed_analysis(
            state,
            state["location"],
            report,
        )

        if report["ready_for_review"]:
            state["stage"] = "awaiting_review"

            reply = (
                "تم تجهيز مسودة البلاغ بنجاح. "
                "راجع الوصف والتصنيف والموقع والمدة في لوحة مسودة البلاغ، "
                "ويمكنك تعديل البيانات أو تنزيل التقرير بصيغة PDF."
            )
        else:
            state["stage"] = "awaiting_details"
            missing = "، ".join(report.get("missing_fields", []))

            reply = (
                f"بقيت بعض المعلومات لاستكمال البلاغ: {missing}. "
                "يرجى تزويدي بالمعلومات الناقصة."
            )

        return response(session_id, state, reply, report)

    def ask_for_location(session_id, state, prefix=""):
        location = state["location"]

        if location.get("area"):
            state["stage"] = "awaiting_confirmation"
            question = (
                location.get("clarification_question_ar")
                or "هل تؤكد الموقع المذكور؟"
            )

            return response(
                session_id,
                state,
                f"{prefix}{question}",
            )

        state["stage"] = "awaiting_area"

        question = (
            location.get("clarification_question_ar")
            or "في أي منطقة أو شارع تقع المشكلة؟"
        )

        return response(
            session_id,
            state,
            f"{prefix}{question}",
        )

    def add_supplement(state, message):
        state["supplemental_text"] = append_text(
            state.get("supplemental_text", ""),
            message,
        )

    @router.post("/api/chat")
    async def chat(payload: ChatRequest):
        message = payload.message.strip()

        if not message:
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty.",
            )

        if payload.session_id and payload.session_id not in SESSIONS:
            raise HTTPException(
                status_code=410,
                detail="انتهت جلسة المحادثة. يرجى بدء بلاغ جديد.",
            )

        session_id = payload.session_id or str(uuid.uuid4())

        if (
            session_id not in SESSIONS
            or SESSIONS[session_id]["stage"] == "completed"
        ):
            state = await start_case(session_id, message)
            return ask_for_location(session_id, state)

        state = SESSIONS[session_id]
        stage = state["stage"]

        if stage == "awaiting_confirmation":
            if is_confirmation(message):
                state["location"] = confirm_location(
                    state["location"],
                    True,
                )
                return build_report(session_id, state)

            if is_rejection(message):
                state["location"] = {
                    "area": None,
                    "area_ar": None,
                    "area_candidates": [],
                    "landmarks": [],
                    "landmarks_ar": [],
                    "direction_cues": [],
                    "coordinates": None,
                    "status": "location_missing",
                    "user_confirmed": False,
                    "needs_clarification": True,
                    "clarification_question_ar": (
                        "ما اسم المنطقة الصحيحة التي يقع فيها البلاغ؟"
                    ),
                }

                state["location_text"] = ""
                state["stage"] = "awaiting_area"

                return response(
                    session_id,
                    state,
                    state["location"]["clarification_question_ar"],
                )

            corrected_areas = find_areas(message)

            if corrected_areas:
                state["location_text"] = message

                refresh_location(
                    state,
                    source_text=message,
                )

                return ask_for_location(session_id, state)

            add_supplement(state, message)
            await refresh_analysis(state)

            current_area = state["location"].get("area")

            refresh_location(
                state,
                source_text=state["location_text"],
                preferred_area=current_area,
            )

            duration, _ = extract_duration(message)

            prefix = (
                "تم تسجيل مدة المشكلة. "
                if duration
                else "تم تسجيل المعلومة الإضافية. "
            )

            return ask_for_location(
                session_id,
                state,
                prefix=prefix,
            )

        if stage == "awaiting_area":
            areas = find_areas(message)

            if areas:
                state["location_text"] = message

                refresh_location(
                    state,
                    source_text=message,
                )

                return ask_for_location(session_id, state)

            add_supplement(state, message)
            state["location_text"] = append_text(
                state["location_text"],
                message,
            )

            await refresh_analysis(state)

            refresh_location(
                state,
                source_text=state["location_text"],
            )

            return ask_for_location(session_id, state)

        if stage == "awaiting_details":
            add_supplement(state, message)
            await refresh_analysis(state)

            state["location"] = confirm_location(
                state["location"],
                True,
            )

            return build_report(session_id, state)

        if stage == "awaiting_review":
            if is_confirmation(message):
                return response(
                    session_id,
                    state,
                    "لتأكيد النسخة النهائية، استخدم زر «تأكيد النسخة النهائية» في لوحة مسودة البلاغ.",
                )

            return response(
                session_id,
                state,
                "يمكنك تعديل البيانات أو تأكيد النسخة النهائية أو تنزيل التقرير من لوحة مسودة البلاغ.",
            )

        raise HTTPException(
            status_code=409,
            detail="حالة المحادثة غير معروفة. ابدأ بلاغاً جديداً.",
        )

    @router.delete("/api/chat/{session_id}")
    async def reset_chat(session_id: str):
        SESSIONS.pop(session_id, None)

        return {
            "message": "تم بدء بلاغ جديد",
            "session_id": session_id,
        }

    return router