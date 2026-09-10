import os, json
from analyze_results import analyze

def test_results_directory_structure():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    results_dir = os.path.join(base_dir, "results")
    
    expected_dirs = [
        os.path.join(results_dir, "clips", "baseline"),
        os.path.join(results_dir, "clips", "rimex"),
        os.path.join(results_dir, "transcripts", "baseline"),
        os.path.join(results_dir, "transcripts", "rimex"),
        os.path.join(results_dir, "metrics"),
        os.path.join(results_dir, "figures"),
    ]
    for d in expected_dirs:
        assert os.path.exists(d), f"Missing required evidence directory: {d}"
        assert os.path.isdir(d)

def test_per_case_evidence_schema():
    analyze()
    base_dir = os.path.dirname(os.path.dirname(__file__))
    evidence_path = os.path.join(base_dir, "results", "per_case_evidence.json")
    assert os.path.exists(evidence_path)

    with open(evidence_path, "r", encoding="utf-8") as f:
        evidence_data = json.load(f)

    assert len(evidence_data) > 0
    sample_cid = next(iter(evidence_data))
    item = evidence_data[sample_cid]

    required_keys = [
        "case_id", "domain", "category", "raw_text",
        "expected_pronunciation", "expected_critical_entities", "evaluations"
    ]
    for k in required_keys:
        assert k in item, f"Missing required evidence key: {k}"

    evals = item["evaluations"]
    assert len(evals) > 0
    sample_eval = evals[0]

    eval_keys = [
        "provider", "variant", "normalized_text", "rime_configuration",
        "audio_clip_path", "transcript_json_path", "hypothesis", "wer",
        "per", "critical_token_accuracy", "latency", "status"
    ]
    for ek in eval_keys:
        assert ek in sample_eval, f"Missing evaluation key: {ek}"

def test_no_secrets_in_results():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    results_dir = os.path.join(base_dir, "results")

    secret_patterns = ["RIME_API_KEY=", "OPENAI_API_KEY=", "ELEVENLABS_API_KEY=", "sk-"]

    for root, _, files in os.walk(results_dir):
        for file in files:
            if file.endswith((".json", ".csv", ".md")):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for secret in secret_patterns:
                        assert secret not in content, f"Possible API secret leak detected in {filepath}: '{secret}'"
