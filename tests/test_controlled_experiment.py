import os, json
from data import TEST_CASES, safe_tune_for_rime
from analyze_results import analyze

def test_pipeline_a_vs_b_prompt_invariants():
    case = TEST_CASES[0]
    raw_text = case["raw_text"]

    # Pipeline A (Baseline untuned)
    pipeline_a_prompt = raw_text

    # Pipeline B (RimeRx tuned)
    pipeline_b_meta = safe_tune_for_rime(raw_text)
    pipeline_b_prompt = pipeline_b_meta["prompt_used"]

    assert pipeline_b_meta["is_safe"] is True
    assert pipeline_a_prompt != pipeline_b_prompt or "Tablet" in pipeline_b_prompt

def test_machine_readable_results_generation():
    # Run analysis export
    analyze()

    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
    metrics_json_path = os.path.join(results_dir, "metrics.json")
    baseline_csv_path = os.path.join(results_dir, "baseline_results.csv")
    rimex_csv_path = os.path.join(results_dir, "rimex_results.csv")
    comparison_csv_path = os.path.join(results_dir, "comparison.csv")

    assert os.path.exists(metrics_json_path)
    assert os.path.exists(baseline_csv_path)
    assert os.path.exists(rimex_csv_path)
    assert os.path.exists(comparison_csv_path)

    with open(metrics_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "summary" in data
        assert "baseline_pipeline_a" in data["summary"]
        assert "rimerx_pipeline_b" in data["summary"]
        assert "improvement_delta" in data["summary"]
