from fastapi.testclient import TestClient
from main import app
from db import export_mos_csv_string
from analyze_results import analyze
import os, json

client = TestClient(app)

def test_blind_session_creation_and_entity_metadata():
    resp = client.post("/api/blind/session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "audio_a_url" in data
    assert "audio_b_url" in data
    assert "critical_entities" in data
    assert isinstance(data["critical_entities"], dict)

def test_mos_rating_submission_with_comprehension_checks():
    session_resp = client.post("/api/blind/session")
    assert session_resp.status_code == 200
    session_data = session_resp.json()

    rating_payload = {
        "session_id": session_data["session_id"],
        "target": "A",
        "naturalness": 5,
        "intelligibility": 4,
        "medication_correct": True,
        "strength_correct": True,
        "dosage_correct": True,
        "duration_correct": True,
        "date_correct": True
    }
    rating_resp = client.post("/api/mos", json=rating_payload)
    assert rating_resp.status_code == 200
    res_data = rating_resp.json()
    assert res_data["session_id"] == session_data["session_id"]
    assert "revealed_provider" in res_data
    assert "revealed_variant" in res_data
    assert res_data["comprehension"]["medication_correct"] is True

def test_mos_csv_export_headers():
    csv_str = export_mos_csv_string()
    assert "medication_correct" in csv_str
    assert "strength_correct" in csv_str
    assert "dosage_correct" in csv_str
    assert "duration_correct" in csv_str
    assert "date_correct" in csv_str

def test_human_evaluation_analysis_non_fabrication():
    analyze()
    base_dir = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(base_dir, "results", "human_evaluation_results.json")
    assert os.path.exists(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "status" in data
    assert "participants_count" in data
