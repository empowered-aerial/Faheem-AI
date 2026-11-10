from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_LABELS = {
    "road_infrastructure": [
        "pothole", "damaged_road_surface", "damaged_sidewalk",
        "damaged_manhole", "road_obstruction",
    ],
    "street_lighting": [
        "light_not_working", "flickering_light", "damaged_pole", "exposed_wiring",
    ],
    "waste_management": [
        "missed_collection", "overflowing_bin", "illegal_dumping", "accumulated_litter",
    ],
    "public_facilities": [
        "damaged_bench", "playground_damage", "park_facility_damage", "public_toilet_issue",
    ],
}

# Candidate references only. These names are not an authoritative gazetteer and have no coordinates.
ABU_DHABI_AREAS = {
    "البطين": "Al Bateen",
    "المشرف": "Al Mushrif",
    "الخالدية": "Al Khalidiyah",
    "المصفح": "Mussafah",
    "مصفح": "Mussafah",
    "مدينة خليفة": "Khalifa City",
    "جزيرة الريم": "Al Reem Island",
    "الريم": "Al Reem Island",
    "الزاهية": "Al Zahiyah",
    "آل نهيان": "Al Nahyan",
    "الروضة": "Al Rawdah",
    "المركزية": "Al Markaziyah",
    "المرور": "Al Muroor",
    "الدانة": "Al Danah",
}

LANDMARKS = [
    "المدرسة", "المدرسه", "المسجد", "المستشفى", "الحديقة", "الحديقه",
    "الممشى", "المول", "المركز التجاري", "محطة البترول", "محطة الوقود",
    "الدوار", "الإشارة", "الاشارة", "الجسر", "النفق", "المبنى", "المركز الصحي",
]
DIRECTION_CUES = ["بجانب", "جنب", "قريب من", "قرب", "مقابل", "قدام", "أمام", "امام", "خلف", "وراء", "عند", "صوب", "باتجاه"]

ISSUE_PATTERNS: dict[str, list[str]] = {
    "pothole": [r"حف(?:رة|ره|رات|ر)", r"هبوط.{0,12}الطريق"],
    "damaged_road_surface": [r"الشارع متكسر", r"الطريق متكسر", r"تلف.{0,12}(?:الشارع|الطريق|الاسفلت|الإسفلت)", r"تكسّر.{0,15}(?:الشارع|الطريق|السطح)"],
    "damaged_sidewalk": [r"رصيف.{0,18}(?:مكسور|متضرر|خربان|متكسر)", r"بلاط الرصيف"],
    "damaged_manhole": [r"منهول", r"غطاء.{0,12}(?:البالوعة|المنهول)"],
    "road_obstruction": [r"عائق في الطريق", r"مخلفات بناء في الطريق", r"شيء في نص الشارع"],
    "light_not_working": [r"(?:اللمبة|لمبة|الإنارة|الانارة|النور).{0,30}(?:ما تشتغل|ما يشتغل|ما تنور|ما يضوي|مطفي|مطفية|خربان|معطل)", r"لمبة.{0,12}(?:خربانة|معطلة)"],
    "flickering_light": [r"(?:اللمبة|الإنارة|الانارة).{0,20}(?:تطفي وتشتغل|ترمش|تومض|تقطع)"],
    "damaged_pole": [r"عمود.{0,18}(?:مكسور|مائل|طايح|متضرر)"],
    "exposed_wiring": [r"(?:سلك|أسلاك|اسلاك).{0,12}مكشوف", r"كيبل مكشوف"],
    "missed_collection": [r"(?:سيارة|شاحنة).{0,25}(?:النظافة|البلدية|جمع النفايات).{0,25}(?:ما مرت|ما جت|ما جاءت|ما وصلت)", r"تأخر جمع النفايات", r"ما تم جمع النفايات"],
    "overflowing_bin": [r"(?:الحاوية|حاوية|الزبالة|سلة المهملات).{0,18}(?:مليانة|فل|فائضة|تفيض|طفح)", r"حاوية ممتلئة"],
    "illegal_dumping": [r"رمي.{0,12}(?:النفايات|المخلفات).{0,12}عشوائي", r"مخلفات مرمية", r"مكب عشوائي"],
    "accumulated_litter": [r"(?:زبالة|نفايات|قمامة|مخلفات).{0,18}(?:متراكمة|متجمعة)", r"تجمع النفايات", r"أكياس زبالة"],
    "damaged_bench": [r"(?:مقعد|كرسي).{0,20}(?:مكسور|خربان|متضرر)"],
    "playground_damage": [r"(?:ألعاب|العاب).{0,25}(?:الأطفال|الاطفال|اليهال).{0,18}(?:خربانة|مكسورة|متضررة)", r"ألعاب الحديقة مكسورة"],
    "park_facility_damage": [r"(?:مرفق|مرافق|سياج).{0,20}(?:الحديقة|المنتزه).{0,20}(?:مكسور|خربان|متضرر)"],
    "public_toilet_issue": [r"(?:حمام|دورة مياه|دورات المياه).{0,20}(?:مسكر|مغلق|خربان|متسخ)"],
}

DURATION_PATTERNS = [
    (r"منذ\s+(?:أمس|امس)", "since yesterday"),
    (r"من\s+(?:أمس|امس)", "since yesterday"),
    (r"من\s+يومين", "for two days"),
    (r"من\s+ثلاثة\s+أيام", "for three days"),
    (r"من\s+أسبوع", "for a week"),
    (r"من\s+أكثر\s+من\s+أسبوع", "for more than a week"),
    (r"من\s+شهر", "for a month"),
    (r"من\s+الصبح|من\s+الصباح", "since morning"),
    (r"من\s+فترة", "for some time"),
]
RISK_PATTERNS = [
    r"خطر", r"حوادث?", r"السيارات تضطر", r"السيارات تتجنب", r"المارة",
    r"الأطفال", r"الاطفال", r"سلك مكشوف", r"حفرة عميقة",
]
NEGATION_PATTERNS = [r"ما في مشكلة", r"ليس هناك", r"مو خربان", r"مش خربان", r"ما خرب", r"تم الإصلاح", r"انصلح", r"تصلح"]


def normalize_arabic(text: str) -> str:
    """Light normalization for model features; original input is always preserved."""
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = text.replace("ـ", "")
    text = re.sub(r"[إأآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ک", "ك").replace("ی", "ي")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_dataset() -> Path | None:
    candidates = [
        DATA_DIR / "FAHEEM_utterances.jsonl",
        DATA_DIR / "utterances.jsonl",
        DATA_DIR / "raw" / "utterances.jsonl",
        ROOT / "FAHEEM_utterances.jsonl",
    ]
    return next((path for path in candidates if path.exists()), None)


def build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    features = FeatureUnion([
        ("word", TfidfVectorizer(
            preprocessor=normalize_arabic,
            analyzer="word",
            ngram_range=(1, 2),
            max_features=35000,
            sublinear_tf=True,
        )),
        ("char", TfidfVectorizer(
            preprocessor=normalize_arabic,
            analyzer="char_wb",
            ngram_range=(2, 5),
            max_features=65000,
            sublinear_tf=True,
        )),
    ])
    return Pipeline([
        ("features", features),
        ("classifier", LogisticRegression(
            max_iter=1200,
            class_weight="balanced",
            C=2.5,
            random_state=42,
        )),
    ])


MODELS: dict[str, Any] = {}
ENGINE_STATUS: dict[str, Any] = {
    "model_ready": False,
    "training_data": None,
    "training_records": 0,
    "model_type": "rule_fallback",
    "variety_model_status": "not_available",
}


def train_or_load_models() -> None:
    import joblib

    dataset_path = find_dataset()
    model_paths = {
        "category": MODEL_DIR / "category_model.joblib",
        "subcategory": MODEL_DIR / "subcategory_model.joblib",
        "variety": MODEL_DIR / "variety_model.joblib",
    }
    metadata_path = MODEL_DIR / "model_metadata.json"
    force_retrain = os.getenv("FAHEEM_RETRAIN", "0") == "1"

    if not force_retrain and all(path.exists() for path in model_paths.values()):
        MODELS.update({name: joblib.load(path) for name, path in model_paths.items()})
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                metadata = {}
        ENGINE_STATUS.update({
            "model_ready": True,
            "model_type": "word_char_tfidf_logistic_regression",
            "training_records": metadata.get("training_records", 0),
            "training_data": metadata.get("training_data"),
            "variety_model_status": metadata.get("variety_model_status", "experimental_synthetic_only"),
            "warning": metadata.get("warning", "Models loaded from local files."),
        })
        return

    if dataset_path is None:
        ENGINE_STATUS["training_data"] = "not_found"
        return

    records: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            text = record.get("text_original", "").strip()
            complaint = record.get("complaint", {})
            variety = record.get("variety", {}).get("label")
            category = complaint.get("category")
            subcategory = complaint.get("subcategory")
            if text and category in CATEGORY_LABELS and subcategory in CATEGORY_LABELS[category] and variety:
                records.append({"text": text, "category": category, "subcategory": subcategory, "variety": variety})

    if len(records) < 100:
        ENGINE_STATUS["training_data"] = str(dataset_path)
        ENGINE_STATUS["training_records"] = len(records)
        ENGINE_STATUS["warning"] = "At least 100 valid labelled records are required to train the prototype."
        return

    texts = [row["text"] for row in records]
    labels = {
        "category": [row["category"] for row in records],
        "subcategory": [row["subcategory"] for row in records],
        "variety": [row["variety"] for row in records],
    }

    for name, y_values in labels.items():
        model = build_pipeline()
        model.fit(texts, y_values)
        MODELS[name] = model
        joblib.dump(model, model_paths[name])

    metadata = {
        "training_data": str(dataset_path.relative_to(ROOT)),
        "training_records": len(records),
        "model_type": "word_char_tfidf_logistic_regression",
        "variety_model_status": "experimental_synthetic_training_data_not_validated",
        "warning": "Training examples are synthetic and pending human review. Scores are not calibrated real-world confidence.",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    ENGINE_STATUS.update({"model_ready": True, **metadata})


def _fallback_classification(text: str) -> tuple[str | None, str | None, float, str | None, float]:
    normalized = normalize_arabic(text)
    matched_subcategory = None
    for label, patterns in ISSUE_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            matched_subcategory = label
            break
    matched_category = next(
        (cat for cat, subcats in CATEGORY_LABELS.items() if matched_subcategory in subcats),
        None,
    )
    if matched_category:
        return matched_category, matched_subcategory, 0.45, None, 0.0
    keyword_groups = {
        "road_infrastructure": ["شارع", "طريق", "رصيف", "حفرة", "منهول"],
        "street_lighting": ["لمبة", "انارة", "مصباح", "كشاف"],
        "waste_management": ["نفايات", "زبالة", "قمامة", "حاوية", "مخلفات"],
        "public_facilities": ["حديقة", "مقعد", "العاب", "حمام", "ملعب"],
    }
    scores = {cat: sum(word in normalized for word in words) for cat, words in keyword_groups.items()}
    if max(scores.values(), default=0) > 0:
        category = max(scores, key=scores.get)
        return category, None, 0.30, None, 0.0
    return None, None, 0.0, None, 0.0


def _model_prediction(model: Any, text: str, allowed: list[str] | None = None) -> tuple[str | None, float]:
    probabilities = model.predict_proba([text])[0]
    classes = list(model.classes_)
    candidates = [(float(prob), str(label)) for label, prob in zip(classes, probabilities) if allowed is None or label in allowed]
    if not candidates:
        return None, 0.0
    confidence, label = max(candidates)
    return label, confidence


def extract_entities(text: str) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []

    def add(label: str, match: re.Match[str], normalized_value: str | None = None) -> None:
        entities.append({
            "label": label,
            "span_text": match.group(0),
            "start_char": match.start(),
            "end_char": match.end(),
            "normalized_value": normalized_value or match.group(0),
            "assertion": "explicit",
        })

    issue_match = None
    issue_label = None
    for label, patterns in ISSUE_PATTERNS.items():
        for pattern in patterns:
            issue_match = re.search(pattern, text, flags=re.IGNORECASE)
            if issue_match:
                issue_label = label
                add("ISSUE_DETAIL", issue_match, label)
                break
        if issue_match:
            break

    duration = None
    for pattern, value in DURATION_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            duration = value
            add("DURATION", match, value)
            break

    area_ar = next((name for name in sorted(ABU_DHABI_AREAS, key=len, reverse=True) if name in text), None)
    area_en = ABU_DHABI_AREAS.get(area_ar) if area_ar else None
    if area_ar:
        match = re.search(re.escape(area_ar), text)
        if match:
            add("LOCATION_AREA", match, area_en)

    landmark = next((item for item in sorted(LANDMARKS, key=len, reverse=True) if item in text), None)
    if landmark:
        match = re.search(re.escape(landmark), text)
        if match:
            add("LOCATION_LANDMARK", match, landmark)

    direction = next((item for item in sorted(DIRECTION_CUES, key=len, reverse=True) if item in text), None)
    if direction:
        match = re.search(re.escape(direction), text)
        if match:
            add("DIRECTIONAL_CUE", match, direction)

    risk_spans = []
    for pattern in RISK_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            if match.group(0) not in risk_spans:
                risk_spans.append(match.group(0))
                add("RISK_EVIDENCE", match, "reported potential risk indicator")

    negated_or_resolved = any(re.search(pattern, text) for pattern in NEGATION_PATTERNS)
    location_specificity = "unresolved"
    if area_ar and landmark:
        location_specificity = "candidate_needs_user_confirmation"
    elif area_ar or landmark:
        location_specificity = "partial_needs_more_detail"

    return {
        "entities": sorted(entities, key=lambda item: (item["start_char"], item["end_char"])),
        "issue_subcategory_from_rules": issue_label,
        "duration": duration,
        "location": {
            "area_ar_candidate": area_ar,
            "area_en_candidate": area_en,
            "landmark_candidate": landmark,
            "directional_cue": direction,
            "coordinates": None,
            "resolution_status": location_specificity,
            "verification_status": "unverified_candidate" if area_ar else "not_resolved",
            "user_confirmed": False,
        },
        "risk_indicators_mentioned": risk_spans,
        "polarity_status": "negated_or_resolved_or_uncertain" if negated_or_resolved else "affirmed_or_unchecked",
    }


def analyze_text(text: str, context: str = "") -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please provide a non-empty Arabic complaint.")

    combined = f"{context.strip()} {text.strip()}".strip() if context.strip() else text.strip()
    category = subcategory = variety = None
    category_confidence = subcategory_confidence = variety_confidence = 0.0
    classification_source = "rule_fallback"

    if ENGINE_STATUS["model_ready"] and MODELS:
        category, category_confidence = _model_prediction(MODELS["category"], combined)
        allowed_subcategories = CATEGORY_LABELS.get(category or "", [])
        subcategory, subcategory_confidence = _model_prediction(MODELS["subcategory"], combined, allowed_subcategories)
        variety, variety_confidence = _model_prediction(MODELS["variety"], combined)
        classification_source = "word_char_tfidf_logistic_regression"
    else:
        category, subcategory, category_confidence, variety, variety_confidence = _fallback_classification(combined)

    entities = extract_entities(combined)
    issue_from_rules = entities["issue_subcategory_from_rules"]
    # Prefer a matching explicit issue phrase over a broad subcategory-model guess.
    if issue_from_rules:
        issue_category = next((cat for cat, labels in CATEGORY_LABELS.items() if issue_from_rules in labels), None)
        if issue_category:
            category = issue_category
            subcategory = issue_from_rules
            subcategory_confidence = max(subcategory_confidence, 0.45)

    missing_fields: list[str] = []
    if not category or category_confidence < 0.25:
        missing_fields.append("complaint_category")
    if not entities["entities"] or not any(e["label"] == "ISSUE_DETAIL" for e in entities["entities"]):
        missing_fields.append("issue_description")
    location = entities["location"]
    if not (location["area_ar_candidate"] or location["landmark_candidate"]):
        missing_fields.append("location")
    elif location["resolution_status"] == "partial_needs_more_detail":
        missing_fields.append("specific_location")

    if "complaint_category" in missing_fields or "issue_description" in missing_fields:
        next_action = "ask_for_issue_detail"
        question = "ممكن توضح المشكلة أكثر؟ هل تتعلق بالطريق أو الإنارة أو النفايات أو أحد المرافق العامة؟"
    elif "location" in missing_fields or "specific_location" in missing_fields:
        next_action = "ask_for_location"
        question = "في أي منطقة أو شارع تقع المشكلة؟ وهل يوجد معلم قريب يساعدنا في تحديد الموقع؟"
    else:
        next_action = "ask_for_confirmation"
        question = "هل يمكنك تأكيد الموقع والتفاصيل قبل تجهيز مسودة البلاغ؟"

    return {
        "request_id": uuid.uuid4().hex[:12],
        "input_text": text.strip(),
        "classification": {
            "category": category,
            "category_confidence_score": round(category_confidence, 4),
            "subcategory": subcategory,
            "subcategory_confidence_score": round(subcategory_confidence, 4),
            "source": classification_source,
        },
        "variety_estimate": {
            "candidate": variety,
            "model_score": round(variety_confidence, 4),
            "status": "experimental_synthetic_only" if variety else "not_available",
        },
        "extraction": entities,
        "completion": {
            "missing_fields": missing_fields,
            "needs_clarification": bool(missing_fields) or next_action == "ask_for_confirmation",
            "next_action": next_action,
            "clarification_question_ar": question,
        },
        "quality_notice": "The classifier is trained on synthetic examples pending human review. Scores are model scores, not calibrated probabilities or proven real-world performance. Dialect estimates are experimental and unvalidated.",
    }


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    context: str = Field(default="", max_length=6000)


app = FastAPI(
    title="FAHEEM Arabic Language Intelligence Engine",
    version="0.1.0",
    description="Prototype NLP API for Arabic civic complaint understanding. Local development only.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def startup() -> None:
    try:
        train_or_load_models()
    except Exception as exc:
        ENGINE_STATUS["model_ready"] = False
        ENGINE_STATUS["startup_error"] = f"{type(exc).__name__}: {exc}"
        print(f"[FAHEEM] Model setup failed; rule fallback will be used: {exc}")

    print("\nFAHEEM Arabic Intelligence Engine")
    print(f"Model ready: {ENGINE_STATUS['model_ready']}")
    print(f"Model type: {ENGINE_STATUS['model_type']}")
    print(f"Training records: {ENGINE_STATUS['training_records']}\n")


@app.get("/", include_in_schema=False)
def home():
    chatbot_file = ROOT / "index.html"
    if chatbot_file.exists():
        return FileResponse(chatbot_file)
    return {"message": "FAHEEM engine is running. Place your chatbot index.html beside faheem_engine.py."}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "engine": "FAHEEM", **ENGINE_STATUS}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict[str, Any]:
    try:
        return analyze_text(payload.text, payload.context)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("faheem_engine:app", host="127.0.0.1", port=8000, reload=False)
