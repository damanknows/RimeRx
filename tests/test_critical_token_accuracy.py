from data import extract_critical_entities
from asr import verify_critical_entities

def test_per_sample_critical_token_accuracy():
    raw_text = "Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"
    raw_entities = extract_critical_entities(raw_text)

    # Perfect ASR transcript
    perfect_asr = "tablet augmentin six hundred twenty five milligrams one zero one five days exp march twenty six"
    res = verify_critical_entities(raw_entities, perfect_asr)

    assert res["critical_token_acc"] == 100.0
    assert res["total_entities"] > 0
    assert res["matched_count"] == res["total_entities"]

def test_per_entity_accuracy_breakdown():
    raw_text = "Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"
    raw_entities = extract_critical_entities(raw_text)

    # Partial ASR transcript (missed 625mg strength)
    partial_asr = "tablet augmentin one zero one five days exp march twenty six"
    res = verify_critical_entities(raw_entities, partial_asr)

    assert "per_entity_results" in res
    assert res["per_entity_results"]["drug"]["matched"] is True
    assert res["per_entity_results"]["dose"]["matched"] is True
    assert res["per_entity_results"]["duration"]["matched"] is True
    assert res["per_entity_results"]["strength"]["matched"] is False

def test_overall_critical_token_accuracy():
    cases = [
        ("Tab Augmentin 625mg 1-0-1 x 5 days", "tablet augmentin six hundred twenty five mg one zero one five days"),
        ("Syp Azithral 200mg/5ml BD for 5 days", "syrup azithral two hundred mg five ml twice daily five days")
    ]

    total_tokens = 0
    matched_tokens = 0

    for raw, asr in cases:
        entities = extract_critical_entities(raw)
        res = verify_critical_entities(entities, asr)
        total_tokens += res["total_entities"]
        matched_tokens += res["matched_count"]

    overall_acc = (matched_tokens / total_tokens * 100) if total_tokens > 0 else 0
    assert overall_acc == 100.0
