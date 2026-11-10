from app.core.exceptions import HealthLinkError


TEST_CATALOG = {
    "CBC": ("Complete blood count", ["CBC", "Full blood count", "FBC"]),
    "LIPID_PANEL": ("Lipid panel", ["Lipid profile", "Cholesterol"]),
    "URINALYSIS": ("Urinalysis", ["Urine routine examination", "Urine R/E"]),
    "URINE_CULTURE": ("Urine culture", ["Urine culture and sensitivity"]),
    "FASTING_GLUCOSE": ("Fasting blood glucose", ["Fasting blood sugar", "FBS"]),
    "HBA1C": ("HbA1c", ["Hemoglobin A1c", "Glycated hemoglobin"]),
    "CREATININE": ("Serum creatinine", ["Creatinine"]),
    "LIVER_PANEL": ("Liver function panel", ["Liver function test", "LFT"]),
    "TSH": ("Thyroid-stimulating hormone", ["TSH"]),
    "CHEST_XRAY": ("Chest X-ray", ["CXR", "Chest radiograph"]),
}


def test_name(code: str) -> str:
    if code not in TEST_CATALOG:
        raise HealthLinkError("Choose a test from the catalog.", status_code=422)
    return TEST_CATALOG[code][0]
