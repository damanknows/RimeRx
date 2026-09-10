from data import TEST_CASES

def test_corpus_size_and_domain():
    assert len(TEST_CASES) >= 200
    for case in TEST_CASES:
        assert "id" in case
        assert "raw_text" in case
        assert "category" in case
        assert "notice" in case
        assert "Synthetic" in case["notice"]

def test_corpus_categories_present():
    categories = set(c.get("category") for c in TEST_CASES)
    expected_categories = [
        "drug_names", "strengths", "dosage_schedules", "frequency",
        "duration", "dates", "abbreviations", "quantities", "indian_english", "adversarial"
    ]
    for exp_cat in expected_categories:
        assert exp_cat in categories

def test_corpus_difficulty_levels():
    difficulties = set(c.get("difficulty") for c in TEST_CASES if "difficulty" in c)
    for exp_diff in ["easy", "medium", "hard", "adversarial"]:
        assert exp_diff in difficulties

def test_required_specific_elements():
    all_raw = " ".join(c["raw_text"] for c in TEST_CASES)

    assert "1-0-1" in all_raw
    assert "0-1-0" in all_raw
    assert "1-1-1" in all_raw
    assert "1/2" in all_raw
    assert "0.5 mg" in all_raw or "0.5mg" in all_raw
    assert "625mg" in all_raw or "625 mg" in all_raw
    assert "1250 mg" in all_raw or "1250mg" in all_raw
    assert "03/26" in all_raw
    assert "B12" in all_raw
    assert "H1N1" in all_raw
