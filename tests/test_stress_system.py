from fastapi.testclient import TestClient
from main import app
from data import STRESS_TEST_CASES, evaluate_stress_case

client = TestClient(app)

def test_stress_corpus_cases():
    assert len(STRESS_TEST_CASES) >= 5
    raw_texts = [c["raw_text"] for c in STRESS_TEST_CASES]
    assert any("Augmentin 625mg 1-0-1" in t for t in raw_texts)
    assert any("Pantocid-DSR" in t for t in raw_texts)
    assert any("1/2 tablet" in t for t in raw_texts)

def test_api_stress_cases_endpoint():
    resp = client.get("/api/stress/cases")
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    assert len(cases) >= 5

def test_evaluate_stress_case_matching():
    raw_text = "Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"
    good_hyp = "Tablet Augmentin six two five milligram one zero one times five days Expiry March twenty six"
    eval_res = evaluate_stress_case(raw_text, good_hyp)
    assert eval_res["overall_matched"] is True
    assert eval_res["accuracy_pct"] == 100.0
    assert eval_res["entities"]["drug"]["matched"] is True
    assert eval_res["entities"]["strength"]["matched"] is True
    assert eval_res["entities"]["dose"]["matched"] is True

def test_evaluate_stress_case_honest_failure():
    raw_text = "Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"
    bad_hyp = "Tablet misheard five days"
    eval_res = evaluate_stress_case(raw_text, bad_hyp)
    assert eval_res["overall_matched"] is False
    assert eval_res["accuracy_pct"] < 100.0
    assert eval_res["limitation_note"] is not None
    assert len(eval_res["failed_fields"]) > 0

def test_api_stress_run_endpoint():
    payload = {"case_id": "stress_001", "provider": "rime"}
    resp = client.post("/api/stress/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "stress_001"
    assert "baseline" in data
    assert "rimerx" in data
    assert "honest_assessment" in data
    assert "entities" in data["rimerx"]["evaluation"]
