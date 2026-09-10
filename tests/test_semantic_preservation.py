from data import validate_semantic_preservation, safe_tune_for_rime, tune_for_rime

def test_drug_preserved():
    raw = "Tab Augmentin 625mg 1-0-1 x 5 days"
    norm = tune_for_rime(raw)
    res = validate_semantic_preservation(raw, norm)
    assert res["is_safe"] is True
    assert "drug" not in res["unpreserved_entities"]

def test_strength_preserved():
    raw = "Paracetamol 500 mg orally twice daily"
    norm = tune_for_rime(raw)
    res = validate_semantic_preservation(raw, norm)
    assert res["is_safe"] is True
    assert "strength" not in res["unpreserved_entities"]

def test_dose_preserved():
    raw = "Tab Dolo 650mg 1-0-1 for 3 days"
    norm = tune_for_rime(raw)
    res = validate_semantic_preservation(raw, norm)
    assert res["is_safe"] is True
    assert "dose" not in res["unpreserved_entities"]

def test_frequency_preserved():
    raw = "Syp Azithral 200mg/5ml BD for 5 days"
    norm = tune_for_rime(raw)
    res = validate_semantic_preservation(raw, norm)
    assert res["is_safe"] is True
    assert "frequency" not in res["unpreserved_entities"]

def test_duration_preserved():
    raw = "Cap Omeprazole 20mg OD for 14 days"
    norm = tune_for_rime(raw)
    res = validate_semantic_preservation(raw, norm)
    assert res["is_safe"] is True
    assert "duration" not in res["unpreserved_entities"]

def test_date_preserved():
    raw = "Prescription date: 10/09/2026 Exp: 03/26"
    norm = tune_for_rime(raw)
    res = validate_semantic_preservation(raw, norm)
    assert res["is_safe"] is True
    assert "date" not in res["unpreserved_entities"]
    assert "expiry" not in res["unpreserved_entities"]

def test_quantity_preserved():
    raw = "Cap Amoxycillin 500mg Qty: 30 caps"
    norm = tune_for_rime(raw)
    res = validate_semantic_preservation(raw, norm)
    assert res["is_safe"] is True
    assert "quantity" not in res["unpreserved_entities"]

def test_unsafe_normalization_rejected():
    raw = "Tab Augmentin 625mg 1-0-1 x 5 days"
    # Simulate an unsafe transformation that alters dosage 625mg to 100mg
    bad_norm = "Tablet Augmentin 100 mg 1 0 1 x 5 days"
    res = validate_semantic_preservation(raw, bad_norm)
    assert res["is_safe"] is False
    assert res["status"] == "UNSAFE_TRANSFORMATION_REJECTED"
    assert "strength" in res["unpreserved_entities"] or len(res["missing_numbers"]) > 0

    # Test safe_tune_for_rime fail-closed fallback
    safe_res = safe_tune_for_rime(raw)
    assert safe_res["is_safe"] is True # Normal tune_for_rime is valid
