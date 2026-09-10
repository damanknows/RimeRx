from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api_config_providers():
    """Verify /api/config exposes PER threshold, max text length, and provider configurations."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "per_threshold" in data
    assert data["per_threshold"] == 5.0
    assert "max_text_length" in data
    assert data["max_text_length"] == 2500
    assert "providers" in data
    assert "rime" in data["providers"]
    assert "openai" in data["providers"]
    assert "elevenlabs" in data["providers"]

def test_render_default_rime_and_timing():
    """Verify rendering with provider 'rime' returns latency metrics and audio_id."""
    payload = {
        "case_id": "rx_synth_001",
        "prompt_type": "default",
        "provider": "rime"
    }
    resp = client.post("/api/render", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "audio_id" in data
    assert "audio_url" in data
    assert data["provider"] == "rime"
    assert "ttfb_ms" in data and isinstance(data["ttfb_ms"], (int, float))
    assert "total_ms" in data and isinstance(data["total_ms"], (int, float))
    assert "cold" in data and isinstance(data["cold"], bool)
    assert data["total_ms"] >= data["ttfb_ms"]

    # Second call should be warm (cold == False)
    resp2 = client.post("/api/render", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["cold"] is False

def test_text_length_rejection():
    """Verify text exceeding 2500 characters is rejected with HTTP 400."""
    long_text = "Tab Augmentin 625mg " * 200
    resp = client.post("/api/render", json={"custom_text": long_text, "prompt_type": "default"})
    assert resp.status_code == 400
    assert "exceeds maximum benchmark limit" in resp.json()["detail"]

def test_api_wer_exact_audio_id():
    """Verify /api/wer accepts audio_id from /api/render and returns WER and per-word analysis."""
    render_resp = client.post("/api/render", json={"case_id": "rx_synth_001", "prompt_type": "default"})
    assert render_resp.status_code == 200
    audio_id = render_resp.json()["audio_id"]

    wer_resp = client.post("/api/wer", json={"audio_id": audio_id, "case_id": "rx_synth_001", "prompt_type": "default"})
    assert wer_resp.status_code == 200
    wer_data = wer_resp.json()
    assert wer_data["audio_id"] == audio_id
    assert "WER" in wer_data and isinstance(wer_data["WER"], (int, float))
    assert "hypothesis" in wer_data
    assert "words" in wer_data and isinstance(wer_data["words"], list)

def test_api_wer_nonexistent_audio_file():
    """Verify /api/wer returns 404 when given a non-existent audio_id."""
    resp = client.post("/api/wer", json={"audio_id": "non_existent_audio_123.mp3", "case_id": "rx_synth_001"})
    assert resp.status_code == 404

def test_blind_mos_session_and_rating():
    """Verify creating a blind evaluation session, submitting a rating, and revealing provider identities."""
    session_resp = client.post("/api/blind/session")
    assert session_resp.status_code == 200
    session_data = session_resp.json()
    session_id = session_data["session_id"]
    assert "session_id" in session_data
    assert "audio_a_url" in session_data
    assert "audio_b_url" in session_data

    # Submit MOS rating for option A
    try:
        rating_payload = {
            "session_id": session_id,
            "target": "A",
            "naturalness": 5,
            "intelligibility": 4
        }
        rating_resp = client.post("/api/mos", json=rating_payload)
        assert rating_resp.status_code == 200
        rating_data = rating_resp.json()
        assert rating_data["session_id"] == session_id
        assert "revealed_provider" in rating_data
        assert "revealed_variant" in rating_data
        assert rating_data["naturalness"] == 5
        assert rating_data["intelligibility"] == 4
    finally:
        from db import get_connection
        conn = get_connection()
        conn.execute("DELETE FROM mos_ratings WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM blind_sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

def test_export_mos_ratings_csv():
    """Verify exporting MOS ratings returns valid CSV formatted data."""
    resp = client.get("/api/mos/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    csv_text = resp.text
    assert "session_id,case_id,provider,variant,naturalness,intelligibility" in csv_text

def test_api_reliability_endpoint():
    """Verify /api/reliability returns provider call statistics."""
    resp = client.get("/api/reliability")
    assert resp.status_code == 200
    data = resp.json()
    assert "rime" in data
    assert "openai" in data
    assert "elevenlabs" in data
    assert data["rime"]["total_calls"] >= 1
    assert data["rime"]["successes"] >= 1

def test_missing_key_graceful_failure_openai(monkeypatch):
    """Verify missing OPENAI_API_KEY returns HTTP 400 with clear message."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    payload = {
        "case_id": "rx_synth_001",
        "prompt_type": "default",
        "provider": "openai"
    }
    resp = client.post("/api/render", json=payload)
    assert resp.status_code == 400
    assert "OPENAI_API_KEY" in resp.json()["detail"]

def test_missing_key_graceful_failure_elevenlabs(monkeypatch):
    """Verify missing ELEVENLABS_API_KEY returns HTTP 400 with clear message."""
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    payload = {
        "case_id": "rx_synth_001",
        "prompt_type": "default",
        "provider": "elevenlabs"
    }
    resp = client.post("/api/render", json=payload)
    assert resp.status_code == 400
    assert "ELEVENLABS_API_KEY" in resp.json()["detail"]

def test_unknown_provider():
    """Verify passing an unknown provider name returns HTTP 400."""
    payload = {
        "case_id": "rx_synth_001",
        "prompt_type": "default",
        "provider": "invalid_provider"
    }
    resp = client.post("/api/render", json=payload)
    assert resp.status_code == 400
    assert "Unknown TTS provider" in resp.json()["detail"]
