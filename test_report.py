
import sys
sys.stdout.reconfigure(encoding="utf-8")

from faheem_location import analyze_location
from faheem_report import generate_civic_report, format_report_ar

complaint = "في حفرة كبيرة في الشارع في البطين قريب من المدرسة من يومين"

analysis = {
    "classification": {
        "category": "road_infrastructure",
        "subcategory": "pothole"
    },
    "entities": {
        "entities": [
            {"type": "ISSUE_DETAIL", "span": "حفرة", "normalized": "pothole"},
            {"type": "LOCATION_AREA", "span": "البطين", "normalized": "Al Bateen"},
            {"type": "DURATION", "span": "من يومين", "normalized": "for two days"}
        ]
    }
}

location = analyze_location(complaint)

report = generate_civic_report(
    complaint_text=complaint,
    analysis=analysis,
    location=location,
    user_confirmed=True
)

print(format_report_ar(report))
