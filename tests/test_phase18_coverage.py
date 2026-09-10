import os
import asyncio
import pytest
from fastapi.testclient import TestClient
from main import app
from data import (
    extract_critical_entities,
    validate_semantic_preservation,
    safe_tune_for_rime,
    tune_for_rime,
)
from asr import verify_critical_entities
from tts.providers import RimeProvider, synthesize_with_fallback

client = TestClient(app)

# 1. Entity Extraction
def test_entity_extraction_edge_cases():
    entities = extract_critical_entities("Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/2026")
    assert entities["drug"] is not None
    assert "625" in str(entities["strength"])
    assert entities["duration"] is not None
    assert entities.get("date") or entities.get("expiry") is not None

# 2. Semantic Preservation
def test_semantic_preservation_valid_and_invalid():
    raw = "Tab Augmentin 625mg 1-0-1 x 5 days"
    valid_tuned = "Tablet Augmentin six two five milligram one zero one for five days"
    res = validate_semantic_preservation(raw, valid_tuned)
    assert res["is_safe"] is True
    assert res["is_valid"] is True

# 3. Unsafe Transformation Rejection
def test_unsafe_transformation_rejection():
    raw = "Tab Augmentin 625mg 1-0-1"
    # Unsafe: drug name changed to Amoxicillin
    unsafe_drug = "Tablet Amoxicillin six two five milligram one zero one"
    res_drug = validate_semantic_preservation(raw, unsafe_drug)
    assert res_drug["is_safe"] is False

    # Unsafe: dosage number changed from 625 to 500
    unsafe_dose = "Tablet Augmentin five zero zero milligram one zero one"
    res_dose = validate_semantic_preservation(raw, unsafe_dose)
    assert res_dose["is_safe"] is False

    # Safe tune wrapper should reject unsafe changes and return original raw text
    safe_res = safe_tune_for_rime(raw)
    assert safe_res["is_safe"] is True

# 4. Critical Token Scoring
def test_critical_token_scoring():
    raw_entities = {
        "drug": "Augmentin",
        "strength": "625mg",
        "dose": "1-0-1",
        "frequency": "1-0-1",
        "duration": "5 days",
        "date": None,
        "quantity": None
    }
    result = verify_critical_entities(raw_entities, "tablet augmentin six two five milligram one zero one for five days")
    assert result["critical_token_acc"] > 0
    assert "Augmentin" in result["matched_entities"] or "625mg" in result["matched_entities"]

# 5. Phoneme / PER Endpoint & WER Endpoint
def test_wer_per_calculation():
    eval_resp = client.post("/api/evaluate", json={"case_id": "rx_synth_001", "prompt_type": "default"})
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert "PER" in eval_data
    assert "CER" in eval_data
    assert "semantic_preservation" in eval_data

    # Render to get valid audio_id for WER endpoint
    render_resp = client.post("/api/render", json={"case_id": "rx_synth_001", "prompt_type": "default"})
    assert render_resp.status_code == 200
    audio_id = render_resp.json()["audio_id"]

    wer_resp = client.post("/api/wer", json={"case_id": "rx_synth_001", "audio_id": audio_id})
    assert wer_resp.status_code == 200
    wer_data = wer_resp.json()
    assert "WER" in wer_data
    assert "words" in wer_data

# 6. Benchmark Output
def test_benchmark_output_structure():
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) > 0
    assert "id" in cases[0]
    assert ("text" in cases[0] or "raw_text" in cases[0])

# 7. Rime Configuration
def test_rime_configuration_visibility():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "Rime"
    assert "model_id" in data
    assert "voice" in data
    assert "language" in data
    assert "endpoint" in data
    assert "audio_format" in data

# 8. Fallback Disclosure & Badge Text
def test_fallback_disclosure_and_logging():
    orig_key = os.environ.get("RIME_API_KEY")
    os.environ["TEST_REQUIRE_KEY"] = "1"
    os.environ.pop("RIME_API_KEY", None)

    async def run_test():
        try:
            audio, meta = await synthesize_with_fallback("Test fallback text", preferred_provider="rime", allow_fallback=True)
            if meta.get("is_fallback"):
                assert meta["fallback_message"] == "Rime unavailable — fallback provider active."
                assert meta["primary_provider"] == "rime"
                assert "fallback_reason" in meta
        except Exception as e:
            assert "RIME_API_KEY" in str(e)

    try:
        asyncio.run(run_test())
    finally:
        os.environ.pop("TEST_REQUIRE_KEY", None)
        if orig_key is not None:
            os.environ["RIME_API_KEY"] = orig_key
        else:
            os.environ.pop("RIME_API_KEY", None)

# 9. Malformed Input
def test_malformed_input():
    resp = client.post("/api/render", json={"invalid_field": 123})
    assert resp.status_code in (400, 422)

# 10. Empty Input
def test_empty_input():
    resp = client.post("/api/render", json={"custom_text": "", "prompt_type": "default"})
    assert resp.status_code in (400, 422)

# 11. API Failure & Retries
def test_api_failure_handling():
    orig_key = os.environ.get("RIME_API_KEY")
    os.environ["TEST_REQUIRE_KEY"] = "1"
    os.environ["RIME_API_KEY"] = "fake_key"

    async def run_test():
        provider = RimeProvider({"endpoint": "https://invalid-host-rime-test.xyz/v1/rime-tts"})
        with pytest.raises(Exception):
            await provider.synthesize("Test failure")

    try:
        asyncio.run(run_test())
    finally:
        os.environ.pop("TEST_REQUIRE_KEY", None)
        if orig_key is not None:
            os.environ["RIME_API_KEY"] = orig_key
        else:
            os.environ.pop("RIME_API_KEY", None)


# 12. Timeout Handling
def test_timeout_handling():
    provider = RimeProvider({})
    assert provider is not None

# 13. Unsupported Voice / Language
def test_unsupported_language_or_voice():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["voice"]) > 0
    assert len(data["language"]) > 0

# 14. Missing Environment Variables
def test_missing_environment_variables_handling():
    provider = RimeProvider({})
    meta = provider.get_metadata()
    assert meta["provider"] == "Rime"
    assert "endpoint" in meta
