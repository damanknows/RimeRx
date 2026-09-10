from data import extract_critical_entities, extract_pharmacy_entities

def test_phase2_example_extraction():
    raw_text = "Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"
    entities = extract_pharmacy_entities(raw_text)

    assert entities["drug"] == "Augmentin"
    assert entities["strength"] == "625mg"
    assert entities["dose"] == "1-0-1"
    assert entities["schedule"] == "1-0-1"
    assert entities["duration"] == "5 days"
    assert entities["expiry"] == "03/26"
    assert "Tab" in entities["abbreviations"]
    assert "Exp" in entities["abbreviations"]

def test_syrup_prescription_extraction():
    raw_text = "Syp. Azithral 200mg/5ml - 5ml BD. Mfg: Alembic. Exp: 03/26."
    entities = extract_pharmacy_entities(raw_text)

    assert entities["drug"] == "Azithral"
    assert entities["strength"] == "200mg/5ml"
    assert entities["dose"] == "5ml"
    assert entities["frequency"] == "BD"
    assert entities["expiry"] == "03/26"
    assert "Syp" in entities["abbreviations"]
    assert "BD" in entities["abbreviations"]
    assert "Mfg" in entities["abbreviations"]
    assert "Exp" in entities["abbreviations"]

def test_paracetamol_dose_extraction():
    raw_text = "Paracetamol 500 mg orally every 6 hours as needed for fever."
    entities = extract_pharmacy_entities(raw_text)

    assert entities["drug"] == "Paracetamol"
    assert entities["strength"] == "500 mg"
    assert entities["frequency"] == "every 6 hours"

def test_capsule_omeprazole_quantity_duration():
    raw_text = "Cap Omeprazole 20mg OD before breakfast for 14 days Qty: 14 caps"
    entities = extract_pharmacy_entities(raw_text)

    assert entities["drug"] == "Omeprazole"
    assert entities["strength"] == "20mg"
    assert entities["frequency"] == "OD"
    assert entities["duration"] == "14 days"
    assert entities["quantity"] in ["14 caps", "14"]
    assert "Cap" in entities["abbreviations"]
    assert "OD" in entities["abbreviations"]
    assert "Qty" in entities["abbreviations"]

def test_backwards_compatibility_keys():
    raw_text = "Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"
    full = extract_critical_entities(raw_text)

    # Legacy list keys must exist and contain extracted data
    assert "drugs" in full and "Augmentin" in full["drugs"]
    assert "strengths" in full and "625mg" in full["strengths"]
    assert "schedules" in full and "1-0-1" in full["schedules"]
    assert "dates" in full and "03/26" in full["dates"]
    assert "numbers" in full and "625" in full["numbers"] and "1" in full["numbers"] and "5" in full["numbers"]

def test_date_and_expiry_distinction():
    text_with_both = "Prescribed on 10/09/2026. Tab Pantocid 40mg OD. Exp: 12/28."
    entities = extract_pharmacy_entities(text_with_both)

    assert entities["drug"] == "Pantocid"
    assert entities["strength"] == "40mg"
    assert entities["frequency"] == "OD"
    assert entities["date"] == "10/09/2026"
    assert entities["expiry"] == "12/28"
