import os, sys, csv, statistics, json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import RESULTS_DIR

CSV_PATH = os.path.join(RESULTS_DIR, "item_results.csv")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "summary.md")
METRICS_JSON_PATH = os.path.join(RESULTS_DIR, "metrics.json")

def analyze():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found. Run 'python scripts/run_benchmark.py' first.")
        return

    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("No rows found in item_results.csv")
        return

    providers = sorted(list(set(r["provider"] for r in rows)))

    provider_stats = {}
    for p in providers:
        provider_stats[p] = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "wer_default": [],
            "wer_tuned": [],
            "per_default": [],
            "per_tuned": [],
            "entity_acc_default": [],
            "entity_acc_tuned": [],
            "ttfb_cold": [],
            "ttfb_warm": [],
            "total_cold": [],
            "total_warm": [],
        }

    category_stats = {}

    for r in rows:
        p = r["provider"]
        variant = r["variant"]
        cat = r["category"]
        status = r["status"]

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "default_wer": [], "tuned_wer": [], "default_per": [], "tuned_per": [], "default_ent": [], "tuned_ent": []}
        category_stats[cat]["total"] += 1

        st = provider_stats[p]
        st["total"] += 1

        if status == "SUCCESS":
            st["success"] += 1
            wer_val = float(r["wer"])
            per_val = float(r["per"])
            ent_val = float(r["entity_acc"])
            ttfb = float(r["ttfb_ms"])
            total_t = float(r["total_ms"])
            is_cold = str(r["cold"]).strip().lower() in ("true", "1")

            if variant == "default":
                st["wer_default"].append(wer_val)
                st["per_default"].append(per_val)
                st["entity_acc_default"].append(ent_val)
                category_stats[cat]["default_wer"].append(wer_val)
                category_stats[cat]["default_per"].append(per_val)
                category_stats[cat]["default_ent"].append(ent_val)
            else:
                st["wer_tuned"].append(wer_val)
                st["per_tuned"].append(per_val)
                st["entity_acc_tuned"].append(ent_val)
                category_stats[cat]["tuned_wer"].append(wer_val)
                category_stats[cat]["tuned_per"].append(per_val)
                category_stats[cat]["tuned_ent"].append(ent_val)

            if is_cold:
                st["ttfb_cold"].append(ttfb)
                st["total_cold"].append(total_t)
            else:
                st["ttfb_warm"].append(ttfb)
                st["total_warm"].append(total_t)
        else:
            st["failed"] += 1

    def mean_or_zero(lst):
        return round(statistics.mean(lst), 2) if lst else 0.0

    print("\n" + "=" * 80)
    print("RIMERX BENCHMARK ANALYSIS SUMMARY")
    print("=" * 80)

    for p, st in provider_stats.items():
        print(f"\nProvider: {p.upper()}")
        print(f"  Total Runs: {st['total']} | Success: {st['success']} | Failed: {st['failed']}")
        print(f"  Default Prompt -> Mean WER: {mean_or_zero(st['wer_default'])}% | Mean PER: {mean_or_zero(st['per_default'])}% | Entity Acc: {mean_or_zero(st['entity_acc_default'])}%")
        print(f"  Tuned Prompt   -> Mean WER: {mean_or_zero(st['wer_tuned'])}% | Mean PER: {mean_or_zero(st['per_tuned'])}% | Entity Acc: {mean_or_zero(st['entity_acc_tuned'])}%")

        wer_diff = mean_or_zero(st['wer_default']) - mean_or_zero(st['wer_tuned'])
        ent_diff = mean_or_zero(st['entity_acc_tuned']) - mean_or_zero(st['entity_acc_default'])
        print(f"  Improvement    -> WER Reduction: {wer_diff:.2f} pts | Entity Acc Gain: {ent_diff:.2f} pts")

        if st['ttfb_cold']:
            print(f"  Cold Run Latency -> TTFB: {mean_or_zero(st['ttfb_cold'])} ms | Total: {mean_or_zero(st['total_cold'])} ms")
        if st['ttfb_warm']:
            print(f"  Warm Run Latency -> TTFB: {mean_or_zero(st['ttfb_warm'])} ms | Total: {mean_or_zero(st['total_warm'])} ms")

    # Generate metrics.json summary for API
    if "rime" in provider_stats:
        rime_st = provider_stats["rime"]
        base_wer = mean_or_zero(rime_st["wer_default"])
        tuned_wer = mean_or_zero(rime_st["wer_tuned"])
        base_per = mean_or_zero(rime_st["per_default"])
        tuned_per = mean_or_zero(rime_st["per_tuned"])
        base_ent = mean_or_zero(rime_st["entity_acc_default"])
        tuned_ent = mean_or_zero(rime_st["entity_acc_tuned"])

        metrics_data = {
            "summary": {
                "total_samples_evaluated": len(rows),
                "baseline_pipeline_a": {
                    "mean_wer": base_wer,
                    "mean_per": base_per,
                    "critical_token_accuracy": base_ent
                },
                "rimerx_pipeline_b": {
                    "mean_wer": tuned_wer,
                    "mean_per": tuned_per,
                    "critical_token_accuracy": tuned_ent
                },
                "improvement_delta": {
                    "wer_reduction_pts": round(base_wer - tuned_wer, 2),
                    "per_reduction_pts": round(base_per - tuned_per, 2),
                    "critical_token_accuracy_gain": round(tuned_ent - base_ent, 2)
                }
            }
        }
        with open(METRICS_JSON_PATH, "w", encoding="utf-8") as f_json:
            json.dump(metrics_data, f_json, indent=2)

if __name__ == "__main__":
    analyze()
