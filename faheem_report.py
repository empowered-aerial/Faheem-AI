
import uuid
from datetime import datetime, timezone, timedelta

CATEGORY_LABELS = {
    "road_infrastructure": "البنية التحتية والطرق",
    "waste_management": "إدارة النفايات",
    "street_lighting": "إنارة الشوارع",
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
    "damaged_sidewalk": "رصيف متضرر",
    "damaged_manhole": "غطاء منهول متضرر",
    "road_obstruction": "عائق في الطريق",
    "streetlight_failure": "تعطل إنارة الشارع",
    "light_not_working": "إنارة لا تعمل",
    "flickering_light": "إنارة متقطعة",
    "broken_streetlight": "عمود إنارة معطل",
    "damaged_pole": "عمود إنارة متضرر",
    "exposed_wiring": "أسلاك كهربائية مكشوفة",
    "illegal_dumping": "إلقاء نفايات بشكل غير قانوني",
    "waste_accumulation": "تراكم النفايات",
    "missed_collection": "عدم جمع النفايات",
    "overflowing_bin": "حاوية نفايات ممتلئة",
    "accumulated_litter": "تراكم المخلفات",
    "water_leak": "تسرب مياه",
    "blocked_drain": "انسداد تصريف المياه",
    "damaged_bench": "مقعد متضرر",
    "playground_damage": "تلف في منطقة الألعاب",
    "park_facility_damage": "مرفق حديقة متضرر",
    "public_toilet_issue": "مشكلة في دورة مياه عامة",
}

DURATION_LABELS = {
    "for one day": "منذ يوم",
    "for two days": "منذ يومين",
    "for three days": "منذ ثلاثة أيام",
    "for a week": "منذ أسبوع",
    "for two weeks": "منذ أسبوعين",
    "since yesterday": "منذ أمس",
    "since today": "منذ اليوم",
    "today": "منذ اليوم",
    "yesterday": "منذ أمس",
    "since this morning": "منذ صباح اليوم",
    "since last night": "منذ الليلة الماضية",
}


def get_entities(analysis):
    if not isinstance(analysis, dict):
        return []

    extraction = analysis.get("extraction", {})
    raw = extraction.get("entities", []) if isinstance(extraction, dict) else []

    if not raw:
        raw = analysis.get("entities", [])

    if isinstance(raw, dict):
        raw = raw.get("entities", [])

    return raw if isinstance(raw, list) else []


def get_entity_value(entities, entity_type):
    for entity in entities:
        if not isinstance(entity, dict):
            continue

        label = entity.get("type") or entity.get("label")

        if label == entity_type:
            return (
                entity.get("normalized")
                or entity.get("normalized_value")
                or entity.get("span")
                or entity.get("span_text")
                or entity.get("text")
            )

    return None


def generate_civic_report(
    complaint_text,
    analysis,
    location,
    user_confirmed=False
):
    analysis = analysis if isinstance(analysis, dict) else {}
    location = location if isinstance(location, dict) else {}

    extraction = analysis.get("extraction", {})
    if not isinstance(extraction, dict):
        extraction = {}

    classification = analysis.get("classification", {})
    if not isinstance(classification, dict):
        classification = {}

    entities = get_entities(analysis)

    category = classification.get("category")
    subcategory = (
        classification.get("subcategory")
        or extraction.get("issue_subcategory_from_rules")
    )

    area = location.get("area")
    confirmed = bool(
        user_confirmed or location.get("user_confirmed", False)
    )

    issue_detail = get_entity_value(entities, "ISSUE_DETAIL")
    duration = (
        get_entity_value(entities, "DURATION")
        or extraction.get("duration")
    )

    landmarks = location.get("landmarks") or []
    landmarks_ar = location.get("landmarks_ar") or []

    description = str(complaint_text or "").strip()

    missing_fields = []

    if not description:
        missing_fields.append("وصف المشكلة")

    if not category:
        missing_fields.append("تصنيف المشكلة")

    if not area:
        missing_fields.append("المنطقة")
    elif not confirmed:
        missing_fields.append("تأكيد الموقع")

    category_ar = CATEGORY_LABELS.get(category, "بلاغ عام")
    subcategory_ar = SUBCATEGORY_LABELS.get(
        subcategory, "غير محدد"
    )

    title = SUBCATEGORY_LABELS.get(
        subcategory,
        category_ar if category else "بلاغ جديد"
    )

    area_ar = location.get("area_ar") or "غير محدد"

    return {
        "report_id": "FAH-" + uuid.uuid4().hex[:8].upper(),
        "created_at": datetime.now(
            timezone(timedelta(hours=4))
        ).isoformat(timespec="seconds"),
        "language": "ar",
        "title_ar": title,
        "category": category,
        "category_ar": category_ar,
        "subcategory": subcategory,
        "subcategory_ar": subcategory_ar,
        "description_original": description,
        "issue_detail": issue_detail,
        "location": {
            "area": area,
            "area_ar": area_ar,
            "landmarks": landmarks,
            "landmarks_ar": landmarks_ar,
            "directions": location.get("direction_cues", []),
            "coordinates": location.get("coordinates"),
            "confirmed": confirmed,
        },
        "duration": duration,
        "duration_ar": DURATION_LABELS.get(
            duration, duration or "غير محددة"
        ),
        "missing_fields": missing_fields,
        "ready_for_review": len(missing_fields) == 0,
        "submission_status": "draft_not_submitted",
    }


def format_report_ar(report):
    location = report.get("location", {})

    if not isinstance(location, dict):
        location = {}

    landmarks = location.get("landmarks_ar") or []

    lines = [
        "ملخص البلاغ المدني",
        "━━━━━━━━━━━━━━━━━━",
        f"رقم البلاغ: {report.get('report_id', 'غير محدد')}",
        f"عنوان البلاغ: {report.get('title_ar', 'بلاغ جديد')}",
        f"التصنيف: {report.get('category_ar', 'بلاغ عام')}",
        f"نوع المشكلة: {report.get('subcategory_ar', 'غير محدد')}",
        "",
        "وصف المشكلة:",
        report.get("description_original") or "غير محدد",
        "",
        "الموقع:",
        location.get("area_ar") or "غير محدد",
        "",
        "معالم قريبة:",
        "، ".join(landmarks) or "غير محدد",
        "",
        "مدة المشكلة:",
        report.get("duration_ar") or "غير محددة",
        "",
        "تأكيد الموقع:",
        "تم التأكيد" if location.get("confirmed") else "بانتظار التأكيد",
        "",
        "حالة البلاغ:",
        "جاهز للمراجعة" if report.get("ready_for_review") else "يحتاج إلى معلومات إضافية",
        "",
        "حالة الإرسال: مسودة — لم يتم إرسال البلاغ",
    ]

    missing = report.get("missing_fields") or []

    if missing:
        lines.extend([
            "",
            "المعلومات الناقصة:",
            "، ".join(missing),
        ])

    return "\n".join(lines)
