
import re
import unicodedata

AREAS = {
    "Al Bateen": {"ar": "البطين", "aliases": ["البطين", "الباتين", "al bateen", "al-bateen"]},
    "Khalidiya": {"ar": "الخالدية", "aliases": ["الخالدية", "الخالديه", "khalidiya", "al khalidiyah"]},
    "Al Zahiyah": {"ar": "الزاهية", "aliases": ["الزاهية", "الزاهيه", "zahiyah", "al zahiyah"]},
    "Al Reem Island": {"ar": "جزيرة الريم", "aliases": ["جزيرة الريم", "الريم", "reem island", "al reem"]},
    "Mussafah": {"ar": "مصفح", "aliases": ["مصفح", "musaffah", "mussafah"]},
    "Mohammed Bin Zayed City": {"ar": "مدينة محمد بن زايد", "aliases": ["مدينة محمد بن زايد", "محمد بن زايد", "mbz city", "mohammed bin zayed"]},
    "Khalifa City": {"ar": "مدينة خليفة", "aliases": ["مدينة خليفة", "خليفة سيتي", "khalifa city"]},
    "Al Mushrif": {"ar": "المشرف", "aliases": ["المشرف", "مشرف", "al mushrif", "mushrif"]},
    "Al Muroor": {"ar": "المرور", "aliases": ["المرور", "muroor", "al muroor"]},
    "Al Markaziyah": {"ar": "المركزية", "aliases": ["المركزية", "المركزيه", "markaziyah"]},
    "Al Nahyan": {"ar": "النهيان", "aliases": ["آل نهيان", "النهيان", "al nahyan"]},
    "Yas Island": {"ar": "جزيرة ياس", "aliases": ["جزيرة ياس", "ياس", "yas island"]},
    "Saadiyat Island": {"ar": "جزيرة السعديات", "aliases": ["جزيرة السعديات", "السعديات", "saadiyat island"]},
    "Al Raha Beach": {"ar": "شاطئ الراحة", "aliases": ["شاطئ الراحة", "الراحة", "al raha", "al raha beach"]},
}

LANDMARKS = {
    "school": ["المدرسة", "مدرسه", "مدرسة", "school"],
    "hospital": ["المستشفى", "مستشفى", "hospital"],
    "mosque": ["المسجد", "مسجد", "mosque"],
    "mall": ["المول", "المركز التجاري", "مول", "mall"],
    "park": ["الحديقة", "حديقة", "park"],
    "roundabout": ["الدوار", "دوار", "roundabout"],
    "bridge": ["الجسر", "جسر", "bridge"],
    "traffic_light": ["الإشارة", "الاشارة", "إشارة", "traffic light"],
    "bus_stop": ["موقف الباص", "موقف الحافلة", "محطة الباص", "bus stop"],
    "petrol_station": ["محطة البترول", "محطة الوقود", "البترول", "petrol station"],
}

LANDMARK_LABELS = {
    "school": "المدرسة",
    "hospital": "المستشفى",
    "mosque": "المسجد",
    "mall": "المركز التجاري",
    "park": "الحديقة",
    "roundabout": "الدوار",
    "bridge": "الجسر",
    "traffic_light": "إشارة المرور",
    "bus_stop": "موقف الحافلات",
    "petrol_station": "محطة الوقود",
}

DIRECTION_CUES = [
    "قريب من", "بالقرب من", "بجانب", "مقابل", "خلف", "أمام",
    "near", "next to", "opposite", "behind", "in front of"
]


def normalize_arabic(text):
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = text.replace("ـ", "")
    text = re.sub(r"[إأآٱ]", "ا", text).replace("ى", "ي")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains(text, phrase):
    normalized_text = normalize_arabic(text)
    normalized_phrase = normalize_arabic(phrase)

    return bool(re.search(
        rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)",
        normalized_text
    ))


def find_areas(text):
    return [
        canonical
        for canonical, details in AREAS.items()
        if any(_contains(text, alias) for alias in details["aliases"])
    ]


def find_matches(text, dictionary):
    return [
        canonical
        for canonical, aliases in dictionary.items()
        if any(_contains(text, alias) for alias in aliases)
    ]


def find_landmarks(text):
    return find_matches(text, LANDMARKS)


def canonicalize_area(value):
    if not value:
        return None

    value = str(value).strip()

    for canonical, details in AREAS.items():
        if normalize_arabic(value) == normalize_arabic(canonical):
            return canonical

        if any(
            normalize_arabic(value) == normalize_arabic(alias)
            for alias in details["aliases"]
        ):
            return canonical

    matches = find_areas(value)
    return matches[0] if len(matches) == 1 else None


def _extract_model_location(analysis):
    if not isinstance(analysis, dict):
        return None

    extraction = analysis.get("extraction", {})

    if not isinstance(extraction, dict):
        return None

    entities = extraction.get("entities", [])

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        if (entity.get("label") or entity.get("type")) == "LOCATION_AREA":
            value = (
                entity.get("normalized_value")
                or entity.get("normalized")
                or entity.get("span_text")
                or entity.get("span")
            )

            area = canonicalize_area(value)

            if area:
                return area

    location = extraction.get("location", {})

    if isinstance(location, dict):
        value = (
            location.get("area_en_candidate")
            or location.get("area_ar_candidate")
        )

        return canonicalize_area(value)

    return None


def analyze_location(
    text,
    analysis=None,
    preferred_area=None,
    context_text=None
):
    areas = find_areas(text)

    context = " ".join(
        part for part in [text, context_text] if part
    )

    landmarks = find_landmarks(context)

    directions = [
        cue for cue in DIRECTION_CUES
        if _contains(context, cue)
    ]

    preferred = canonicalize_area(preferred_area)

    if preferred:
        area = preferred
        areas = [preferred]
    elif len(areas) == 1:
        area = areas[0]
    elif len(areas) > 1:
        area = None
    else:
        area = _extract_model_location(analysis)

    if len(areas) > 1 and not preferred:
        status = "multiple_areas_need_clarification"
        question = "ذكرت أكثر من منطقة. في أي منطقة يقع البلاغ تحديداً؟"

    elif not area:
        status = "location_missing"
        question = "في أي منطقة أو شارع تقع المشكلة؟"

    else:
        status = "candidate_needs_user_confirmation"
        area_ar = AREAS[area]["ar"]

        nearby = (
            " بالقرب من " + " و".join(
                LANDMARK_LABELS[item] for item in landmarks
            )
            if landmarks else ""
        )

        question = (
            f"هل تؤكد أن موقع المشكلة هو {area_ar}{nearby}؟"
        )

    return {
        "area": area,
        "area_ar": AREAS[area]["ar"] if area else None,
        "area_candidates": areas or ([area] if area else []),
        "landmarks": landmarks,
        "landmarks_ar": [
            LANDMARK_LABELS[item] for item in landmarks
        ],
        "direction_cues": directions,
        "coordinates": None,
        "status": status,
        "user_confirmed": False,
        "needs_clarification": True,
        "clarification_question_ar": question,
    }


def confirm_location(location_result, confirmed):
    result = dict(location_result)
    result["user_confirmed"] = bool(confirmed)
    result["needs_clarification"] = not bool(confirmed)

    if confirmed and result.get("area"):
        result["status"] = "confirmed"
        result["clarification_question_ar"] = None
    else:
        result["status"] = "not_confirmed"
        result["clarification_question_ar"] = (
            "يرجى توضيح المنطقة أو اختيار الموقع الصحيح."
        )

    return result
