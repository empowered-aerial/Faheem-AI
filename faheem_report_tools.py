from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

CATEGORY_LABELS = {
    "road_infrastructure": "البنية التحتية والطرق",
    "street_lighting": "إنارة الشوارع",
    "waste_management": "إدارة النفايات",
    "public_facilities": "المرافق العامة",
    "water_supply": "إمدادات المياه",
    "drainage": "تصريف مياه الأمطار",
    "traffic": "السلامة المرورية",
    "other": "بلاغ عام",
}

SUBCATEGORY_LABELS = {
    "pothole": "حفرة في الطريق",
    "damaged_road": "طريق متضرر",
    "road_damage": "تلف الطريق",
    "damaged_road_surface": "تلف سطح الطريق",
    "damaged_sidewalk": "تلف الرصيف",
    "damaged_manhole": "غطاء منهول تالف",
    "road_obstruction": "عائق في الطريق",
    "light_not_working": "إنارة لا تعمل",
    "streetlight_failure": "تعطل إنارة الشارع",
    "broken_streetlight": "عمود إنارة معطل",
    "flickering_light": "إنارة متقطعة",
    "damaged_pole": "عمود إنارة تالف",
    "exposed_wiring": "أسلاك مكشوفة",
    "missed_collection": "تأخر جمع النفايات",
    "overflowing_bin": "حاوية ممتلئة",
    "illegal_dumping": "رمي نفايات عشوائي",
    "accumulated_litter": "تراكم النفايات",
    "waste_accumulation": "تراكم النفايات",
    "water_leak": "تسرب مياه",
    "blocked_drain": "انسداد تصريف المياه",
    "damaged_bench": "مقعد تالف",
    "playground_damage": "تلف ألعاب الأطفال",
    "park_facility_damage": "تلف مرفق عام",
    "public_toilet_issue": "مشكلة في دورة المياه العامة",
}

CATEGORY_SUBCATEGORIES = {
    "road_infrastructure": [
        "pothole", "damaged_road", "road_damage",
        "damaged_road_surface", "damaged_sidewalk",
        "damaged_manhole", "road_obstruction"
    ],
    "street_lighting": [
        "light_not_working", "streetlight_failure",
        "broken_streetlight", "flickering_light",
        "damaged_pole", "exposed_wiring"
    ],
    "waste_management": [
        "missed_collection", "overflowing_bin",
        "illegal_dumping", "accumulated_litter",
        "waste_accumulation"
    ],
    "public_facilities": [
        "damaged_bench", "playground_damage",
        "park_facility_damage", "public_toilet_issue"
    ],
    "water_supply": ["water_leak"],
    "drainage": ["blocked_drain"],
    "traffic": ["road_obstruction"],
}

REPORTS: dict[str, dict[str, Any]] = {}
_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value: Any, limit: int = 5000) -> str:
    return str(value or "").strip()[:limit]


def _location(report: dict[str, Any]) -> dict[str, Any]:
    value = report.get("location")
    if not isinstance(value, dict):
        value = {}
        report["location"] = value
    return value


def _description(report: dict[str, Any]) -> str:
    return _text(
        report.get("description_original")
        or report.get("issue_description")
        or report.get("original_text")
    )


def _area(loc: dict[str, Any]) -> str:
    return _text(
        loc.get("area_ar")
        or loc.get("area_ar_candidate")
        or loc.get("area")
        or loc.get("area_en_candidate"),
        300
    )


def _landmark(loc: dict[str, Any]) -> str:
    candidate = loc.get("landmark_candidate")
    if candidate:
        return _text(candidate, 300)

    for key in ("landmarks_ar", "landmarks"):
        value = loc.get(key)
        if isinstance(value, list) and value:
            return _text("، ".join(str(x) for x in value if x), 500)
        if isinstance(value, str) and value.strip():
            return _text(value, 500)

    return ""


def _coords(value: Any) -> dict[str, float] | None:
    if value is None or value == "":
        return None

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        lat, lon = value[0], value[1]
    elif isinstance(value, dict):
        lat = value.get("latitude", value.get("lat"))
        lon = value.get(
            "longitude",
            value.get("lon", value.get("lng", value.get("long")))
        )
    else:
        return None

    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Invalid map coordinates.")

    if not (22.0 <= lat <= 27.0 and 51.0 <= lon <= 57.5):
        raise HTTPException(
            status_code=422,
            detail="Choose a point within the UAE pilot area."
        )

    return {
        "latitude": round(lat, 6),
        "longitude": round(lon, 6)
    }


def _set_location_text(
    loc: dict[str, Any],
    area: str,
    landmark: str,
    direction: str
) -> None:
    if "area_ar_candidate" in loc or "area_en_candidate" in loc:
        loc["area_ar_candidate"] = area or None
        loc["area_en_candidate"] = None
        loc["landmark_candidate"] = landmark or None
        loc["directional_cue"] = direction or None
    else:
        loc["area"] = area or None
        loc["area_ar"] = area or None
        loc["landmarks"] = [landmark] if landmark else []
        loc["landmarks_ar"] = [landmark] if landmark else []
        loc["directions"] = [direction] if direction else []

    loc["original_expression"] = "، ".join(
        x for x in (area, direction, landmark) if x
    ) or None

    loc["user_confirmed"] = False
    loc["confirmed"] = False
    loc["verification_status"] = "unverified_candidate"
    loc["resolution_status"] = "candidate_needs_user_confirmation"


def _refresh_missing(report: dict[str, Any]) -> list[str]:
    loc = _location(report)
    missing = []

    if not report.get("category"):
        missing.append("category")

    if not _description(report):
        missing.append("description")

    if not (_area(loc) or _landmark(loc) or loc.get("coordinates")):
        missing.append("location")

    report["missing_fields"] = missing
    report["ready_for_review"] = len(missing) == 0

    return missing


def create_report_tools_router() -> APIRouter:
    router = APIRouter()

    @router.put("/api/reports/{session_id}")
    def save_report(
        session_id: str,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        report = payload.get("report")

        if not isinstance(report, dict) or not report.get("report_id"):
            raise HTTPException(
                status_code=422,
                detail="A valid report object is required."
            )

        with _LOCK:
            existing = REPORTS.get(session_id)

            if existing and existing.get("report_id") == report.get("report_id"):
                saved = copy.deepcopy(existing)
            else:
                saved = copy.deepcopy(report)
                saved.setdefault("submission_status", "draft_not_submitted")
                saved.setdefault("status", "draft")
                saved.setdefault("created_at", _now())
                saved["updated_at"] = _now()
                REPORTS[session_id] = saved

            return {
                "session_id": session_id,
                "report": copy.deepcopy(saved)
            }

    @router.get("/api/reports/{session_id}")
    def get_saved_report(session_id: str) -> dict[str, Any]:
        with _LOCK:
            report = REPORTS.get(session_id)

            if report is None:
                raise HTTPException(
                    status_code=404,
                    detail="No saved report for this session."
                )

            return {
                "session_id": session_id,
                "report": copy.deepcopy(report)
            }

    @router.patch("/api/reports/{session_id}")
    def update_report(
        session_id: str,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        with _LOCK:
            report = REPORTS.get(session_id)

            if report is None:
                raise HTTPException(
                    status_code=404,
                    detail="Report not found. Start or restore the complaint first."
                )

            description = payload.get("description")

            if description is not None:
                description = _text(description)

                if not description:
                    raise HTTPException(
                        status_code=422,
                        detail="Description cannot be empty."
                    )

                if "description_original" in report or "issue_detail" in report:
                    report["description_original"] = description

                if "issue_description" in report:
                    report["issue_description"] = description

                if not any(
                    key in report
                    for key in ("description_original", "issue_description")
                ):
                    report["original_text"] = description

            category = payload.get("category")

            if category is not None:
                if category not in CATEGORY_LABELS:
                    raise HTTPException(
                        status_code=422,
                        detail="Unsupported report category."
                    )

                report["category"] = category

                if "category_ar" in report or "category_label_ar" not in report:
                    report["category_ar"] = CATEGORY_LABELS[category]

                if "category_label_ar" in report:
                    report["category_label_ar"] = CATEGORY_LABELS[category]

                if (
                    report.get("subcategory")
                    and report["subcategory"] not in CATEGORY_SUBCATEGORIES.get(category, [])
                ):
                    report["subcategory"] = None
                    report["subcategory_ar"] = "غير محدد"
                    report["subcategory_label_ar"] = "غير محدد"

            subcategory = payload.get("subcategory")

            if subcategory is not None:
                if subcategory not in SUBCATEGORY_LABELS:
                    raise HTTPException(
                        status_code=422,
                        detail="Unsupported issue type."
                    )

                report["subcategory"] = subcategory
                report["subcategory_ar"] = SUBCATEGORY_LABELS[subcategory]
                report["subcategory_label_ar"] = SUBCATEGORY_LABELS[subcategory]
                report["title_ar"] = SUBCATEGORY_LABELS[subcategory]

            if payload.get("duration") is not None:
                duration = _text(payload.get("duration"), 200)
                report["duration"] = duration or None
                report["duration_ar"] = duration or "غير محددة"

            loc = _location(report)

            location_changed = any(
                key in payload
                for key in ("area", "landmark", "direction", "coordinates")
            )

            if location_changed:
                area = _text(payload.get("area", _area(loc)), 300)
                landmark = _text(payload.get("landmark", _landmark(loc)), 300)

                if isinstance(loc.get("directions"), list):
                    existing_direction = (
                        loc.get("directional_cue")
                        or (loc.get("directions") or [""])[0]
                    )
                else:
                    existing_direction = loc.get("directional_cue", "")

                direction = _text(
                    payload.get("direction", existing_direction),
                    100
                )

                _set_location_text(loc, area, landmark, direction)

                if "coordinates" in payload:
                    loc["coordinates"] = _coords(payload.get("coordinates"))

            missing = _refresh_missing(report)

            report["updated_at"] = _now()
            report["pending_confirmations"] = []

            if "status" in report:
                report["status"] = "draft"

            report["submission_status"] = "draft_not_submitted"

            report.pop("confirmed_at", None)
            report["user_approved"] = False

            return {
                "session_id": session_id,
                "report": copy.deepcopy(report),
                "missing_fields": missing
            }

    @router.post("/api/reports/{session_id}/confirm")
    def confirm_report(session_id: str) -> dict[str, Any]:
        with _LOCK:
            report = REPORTS.get(session_id)

            if report is None:
                raise HTTPException(
                    status_code=404,
                    detail="Report not found."
                )

            missing = _refresh_missing(report)

            if missing:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Complete the required report fields first.",
                        "missing_fields": missing
                    }
                )

            loc = _location(report)
            loc["user_confirmed"] = True
            loc["confirmed"] = True
            loc["verification_status"] = (
                "user_confirmed_description_not_gis_verified"
            )

            report["status"] = "confirmed_not_submitted"
            report["submission_status"] = "not_submitted"
            report["pending_confirmations"] = []
            report["user_approved"] = True
            report["confirmed_at"] = _now()
            report["updated_at"] = _now()
            report["ready_for_review"] = True

            return {
                "session_id": session_id,
                "report": copy.deepcopy(report),
                "message_ar": "تم تأكيد مسودة البلاغ. لم يتم إرسالها إلى أي جهة."
            }

    @router.delete("/api/reports/{session_id}")
    def delete_report(session_id: str) -> dict[str, Any]:
        with _LOCK:
            removed = REPORTS.pop(session_id, None) is not None

        return {
            "session_id": session_id,
            "deleted": removed
        }

    return router