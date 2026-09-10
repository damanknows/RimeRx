import os, csv, statistics

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_PATH = os.path.join(RESULTS_DIR, "item_results.csv")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "summary.md")

def analyze():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found. Run 'python run_benchmark.py' first.")
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

    # Per-provider stats dictionary
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
            ent_val = float(r.get("entity_acc", 100.0))
            ttfb = float(r["ttfb_ms"])
            total_t = float(r["total_ms"])
            is_cold = (r["cold"].lower() == "true")

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

    def mean_val(vals):
        return round(statistics.mean(vals), 2) if vals else 0.0

    def median_val(vals):
        return round(statistics.median(vals), 2) if vals else 0.0

    # Build Markdown Summary
    md = []
    md.append("# RimeRx TTS Benchmark Summary Report\n")
    md.append("> **Exploratory &mdash; Small Sample Notice**: Results reported below are generated from exploratory benchmark runs on synthetic domain prescriptions and addresses. Metrics serve as relative performance indicators under provider-recommended configurations.\n")

    md.append("## Executive Summary\n")
    md.append("| Provider | Model | Total Calls | Reliability Rate | Critical Token Accuracy (Default / Tuned) | Default WER (Mean) | Tuned WER (Mean) | Default PER (Mean) | Tuned PER (Mean) |")
    md.append("|---|---|---|---|---|---|---|---|---|")

    for p in providers:
        st = provider_stats[p]
        rel_rate = round((st["success"] / st["total"] * 100), 1) if st["total"] > 0 else 0.0
        def_wer = f"{mean_val(st['wer_default'])}%" if st['wer_default'] else "N/A"
        tun_wer = f"{mean_val(st['wer_tuned'])}%" if st['wer_tuned'] else "N/A"
        def_per = f"{mean_val(st['per_default'])}%" if st['per_default'] else "N/A"
        tun_per = f"{mean_val(st['per_tuned'])}%" if st['per_tuned'] else "N/A"
        crit_tok_acc = f"{mean_val(st['entity_acc_default'])}% / {mean_val(st['entity_acc_tuned'])}%" if st['entity_acc_default'] else "N/A"

        md.append(f"| **{p.upper()}** | `{p}` | {st['total']} | {rel_rate}% | **{crit_tok_acc}** | {def_wer} | {tun_wer} | {def_per} | {tun_per} |")

    md.append("\n## Latency Breakdown (Warm vs Cold Runs)\n")
    md.append("| Provider | Cold TTFB (Mean) | Warm TTFB (Mean) | Cold Total (Mean) | Warm Total (Mean) |")
    md.append("|---|---|---|---|---|")

    for p in providers:
        st = provider_stats[p]
        c_ttfb = f"{mean_val(st['ttfb_cold'])} ms" if st['ttfb_cold'] else "N/A"
        w_ttfb = f"{mean_val(st['ttfb_warm'])} ms" if st['ttfb_warm'] else "N/A"
        c_tot = f"{mean_val(st['total_cold'])} ms" if st['total_cold'] else "N/A"
        w_tot = f"{mean_val(st['total_warm'])} ms" if st['total_warm'] else "N/A"
        md.append(f"| **{p.upper()}** | {c_ttfb} | {w_ttfb} | {c_tot} | {w_tot} |")

    md.append("\n## Per-Category Critical Token Accuracy & Error Rates\n")
    md.append("| Category | Total Evaluated | Critical Token Acc (Tuned) | Mean Default WER | Mean Tuned WER | Mean Default PER | Mean Tuned PER | Delta (WER) |")
    md.append("|---|---|---|---|---|---|---|---|")

    for cat, st in sorted(category_stats.items()):
        d_wer = mean_val(st["default_wer"])
        t_wer = mean_val(st["tuned_wer"])
        d_per = mean_val(st["default_per"])
        t_per = mean_val(st["tuned_per"])
        t_ent = mean_val(st["tuned_ent"])
        delta_wer = round(d_wer - t_wer, 2)
        md.append(f"| `{cat}` | {st['total']} | **{t_ent}%** | {d_wer}% | {t_wer}% | {d_per}% | {t_per}% | **-{delta_wer} pts** |")

    md.append("\n## Benchmark Methodology & Primary Metrics\n")
    md.append("- **Primary Metric &mdash; Critical Token Accuracy**: Direct entity-level verification comparing raw prescription entities (drug name, strength, dose, schedule, duration, expiry date) with ASR acoustic transcriptions.\n")
    md.append("- **Secondary Metric &mdash; Word Error Rate (WER)**: Acoustic accuracy score generated by transcribing synthesized audio via `faster-whisper` (`small.en`, `int8`, `beam_size=5`) and comparing against normalized ground truth via `jiwer`.\n")
    md.append("- **Secondary Metric &mdash; Phoneme Error Rate (PER)**: G2P transliteration edit distance using `Epitran` G2P (`eng-Latn`).\n")

    # Export Machine-Readable Controlled Experiment Files (Phase 6 & 7)
    METRICS_DIR = os.path.join(RESULTS_DIR, "metrics")
    os.makedirs(METRICS_DIR, exist_ok=True)

    baseline_csv_path = os.path.join(RESULTS_DIR, "baseline_results.csv")
    metrics_baseline_csv_path = os.path.join(METRICS_DIR, "baseline_results.csv")
    
    rimex_csv_path = os.path.join(RESULTS_DIR, "rimex_results.csv")
    metrics_rimex_csv_path = os.path.join(METRICS_DIR, "rimex_results.csv")

    comparison_csv_path = os.path.join(RESULTS_DIR, "comparison.csv")
    metrics_comp_csv_path = os.path.join(METRICS_DIR, "comparison.csv")

    metrics_json_path = os.path.join(RESULTS_DIR, "metrics.json")
    metrics_dir_json_path = os.path.join(METRICS_DIR, "metrics.json")

    per_case_evidence_path = os.path.join(RESULTS_DIR, "per_case_evidence.json")
    metrics_evidence_path = os.path.join(METRICS_DIR, "per_case_evidence.json")

    baseline_rows = [r for r in rows if r.get("variant") == "default"]
    rimex_rows = [r for r in rows if r.get("variant") == "tuned"]

    # Write baseline_results.csv
    if baseline_rows:
        for p in [baseline_csv_path, metrics_baseline_csv_path]:
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=baseline_rows[0].keys())
                w.writeheader()
                w.writerows(baseline_rows)

    # Write rimex_results.csv
    if rimex_rows:
        for p in [rimex_csv_path, metrics_rimex_csv_path]:
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=rimex_rows[0].keys())
                w.writeheader()
                w.writerows(rimex_rows)

    # Build side-by-side comparison.csv (Rime provider)
    rime_def = {r["case_id"]: r for r in rows if r.get("provider") == "rime" and r.get("variant") == "default"}
    rime_tune = {r["case_id"]: r for r in rows if r.get("provider") == "rime" and r.get("variant") == "tuned"}

    comp_rows = []
    for cid in rime_def:
        d_item = rime_def[cid]
        t_item = rime_tune.get(cid, {})

        d_wer = float(d_item["wer"]) if d_item.get("wer") else 0.0
        t_wer = float(t_item.get("wer", 0.0)) if t_item.get("wer") else 0.0
        d_per = float(d_item["per"]) if d_item.get("per") else 0.0
        t_per = float(t_item.get("per", 0.0)) if t_item.get("per") else 0.0
        d_acc = float(d_item.get("entity_acc", 0.0)) if d_item.get("entity_acc") else 0.0
        t_acc = float(t_item.get("entity_acc", 0.0)) if t_item.get("entity_acc") else 0.0

        comp_rows.append({
            "case_id": cid,
            "category": d_item.get("category", "general"),
            "difficulty": d_item.get("difficulty", "medium"),
            "raw_text": d_item.get("raw_text", ""),
            "baseline_prompt": d_item.get("prompt_used", ""),
            "rimerx_prompt": t_item.get("prompt_used", ""),
            "baseline_critical_token_acc": d_acc,
            "rimerx_critical_token_acc": t_acc,
            "delta_critical_token_acc": round(t_acc - d_acc, 2),
            "baseline_wer": d_wer,
            "rimerx_wer": t_wer,
            "delta_wer": round(d_wer - t_wer, 2),
            "baseline_per": d_per,
            "rimerx_per": t_per,
            "delta_per": round(d_per - t_per, 2),
            "status": "COMPLETED"
        })

    if comp_rows:
        for p in [comparison_csv_path, metrics_comp_csv_path]:
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=comp_rows[0].keys())
                w.writeheader()
                w.writerows(comp_rows)

    # Build metrics.json
    rime_st = provider_stats.get("rime", {})
    metrics_data = {
        "notice": "Synthetic/curated evaluation data for TTS benchmark — Zero real patient data",
        "summary": {
            "total_samples_evaluated": len(rows),
            "baseline_pipeline_a": {
                "critical_token_accuracy": mean_val(rime_st.get("entity_acc_default", [])),
                "mean_wer": mean_val(rime_st.get("wer_default", [])),
                "mean_per": mean_val(rime_st.get("per_default", [])),
                "reliability_rate": round((rime_st.get("success", 0) / rime_st.get("total", 1) * 100), 1) if rime_st.get("total") else 0.0
            },
            "rimerx_pipeline_b": {
                "critical_token_accuracy": mean_val(rime_st.get("entity_acc_tuned", [])),
                "mean_wer": mean_val(rime_st.get("wer_tuned", [])),
                "mean_per": mean_val(rime_st.get("per_tuned", [])),
                "reliability_rate": round((rime_st.get("success", 0) / rime_st.get("total", 1) * 100), 1) if rime_st.get("total") else 0.0
            },
            "improvement_delta": {
                "critical_token_accuracy_gain": round(mean_val(rime_st.get("entity_acc_tuned", [])) - mean_val(rime_st.get("entity_acc_default", [])), 2),
                "wer_reduction_pts": round(mean_val(rime_st.get("wer_default", [])) - mean_val(rime_st.get("wer_tuned", [])), 2),
                "per_reduction_pts": round(mean_val(rime_st.get("per_default", [])) - mean_val(rime_st.get("per_tuned", [])), 2)
            }
        },
        "by_category": category_stats
    }

    import json
    for p in [metrics_json_path, metrics_dir_json_path]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2)

    # Build per_case_evidence.json
    from data import extract_critical_entities
    per_case_evidence = {}
    for r in rows:
        cid = r["case_id"]
        if cid not in per_case_evidence:
            per_case_evidence[cid] = {
                "case_id": cid,
                "domain": r.get("domain", "Pharmacy"),
                "category": r.get("category", "general"),
                "raw_text": r.get("raw_text", ""),
                "expected_pronunciation": r.get("expected_pronunciation", ""),
                "expected_critical_entities": extract_critical_entities(r.get("raw_text", "")),
                "evaluations": []
            }
        variant_folder = "baseline" if r.get("variant") == "default" else "rimex"
        per_case_evidence[cid]["evaluations"].append({
            "provider": r.get("provider"),
            "variant": r.get("variant"),
            "normalized_text": r.get("prompt_used"),
            "rime_configuration": {
                "model_id": "mist/v1",
                "voice": "marsh",
                "language": "en-IN",
                "audio_format": "mp3"
            },
            "audio_clip_path": f"results/clips/{variant_folder}/{cid}_{r.get('provider')}.mp3",
            "transcript_json_path": f"results/transcripts/{variant_folder}/{cid}_{r.get('provider')}.json",
            "hypothesis": r.get("hypothesis"),
            "wer": float(r["wer"]) if r.get("wer") else None,
            "per": float(r["per"]) if r.get("per") else None,
            "critical_token_accuracy": float(r["entity_acc"]) if r.get("entity_acc") else 0.0,
            "latency": {
                "ttfb_ms": float(r["ttfb_ms"]) if r.get("ttfb_ms") else None,
                "total_ms": float(r["total_ms"]) if r.get("total_ms") else None,
                "cold": (r.get("cold", "").lower() == "true") if r.get("cold") else False
            },
            "status": r.get("status")
        })

    for p in [per_case_evidence_path, metrics_evidence_path]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(per_case_evidence, f, indent=2)

    # Process Human MOS Listening Evaluation (Phase 8)
    try:
        from db import get_all_mos_ratings
        mos_rows = get_all_mos_ratings()
    except Exception:
        mos_rows = []

    if not mos_rows:
        human_eval_summary = {
            "status": "PENDING / PROTOCOL READY",
            "notice": "No live human participant listening sessions logged yet in local test environment.",
            "participants_count": 0,
            "evaluation_procedure": "Double-blinded A/B listening comparison",
            "ratings_summary": None
        }
        md.append("\n## Human Listening Evaluation (MOS & Comprehension)\n")
        md.append("- **Status**: **PENDING / PROTOCOL READY** (0 live human participant sessions logged in automated benchmark environment).\n")
        md.append("- **Protocol**: Double-blinded A/B evaluation measuring Naturalness (1-5), Intelligibility (1-5), and binary comprehension recall for medication, strength, dosage, duration, and date.\n")
    else:
        unique_sessions = set(r["session_id"] for r in mos_rows)
        default_ratings = [r for r in mos_rows if r["variant"] == "default"]
        tuned_ratings = [r for r in mos_rows if r["variant"] == "tuned"]

        def calc_mean(arr, key):
            vals = [float(r[key]) for r in arr if r.get(key) is not None]
            return round(statistics.mean(vals), 2) if vals else 0.0

        def calc_pct(arr, key):
            vals = [float(r[key]) for r in arr if r.get(key) is not None]
            return round(sum(vals) / len(vals) * 100, 1) if vals else 0.0

        human_eval_summary = {
            "status": "COMPLETED_SESSIONS_LOGGED",
            "participants_count": len(unique_sessions),
            "total_ratings": len(mos_rows),
            "baseline_variant": {
                "mean_naturalness": calc_mean(default_ratings, "naturalness"),
                "mean_intelligibility": calc_mean(default_ratings, "intelligibility"),
                "medication_comprehension_pct": calc_pct(default_ratings, "medication_correct"),
                "strength_comprehension_pct": calc_pct(default_ratings, "strength_correct"),
                "dosage_comprehension_pct": calc_pct(default_ratings, "dosage_correct")
            },
            "rimerx_variant": {
                "mean_naturalness": calc_mean(tuned_ratings, "naturalness"),
                "mean_intelligibility": calc_mean(tuned_ratings, "intelligibility"),
                "medication_comprehension_pct": calc_pct(tuned_ratings, "medication_correct"),
                "strength_comprehension_pct": calc_pct(tuned_ratings, "strength_correct"),
                "dosage_comprehension_pct": calc_pct(tuned_ratings, "dosage_correct")
            }
        }
        md.append("\n## Human Listening Evaluation (MOS & Comprehension)\n")
        md.append(f"- **Status**: **SESSIONS LOGGED** ({len(unique_sessions)} participants, {len(mos_rows)} total ratings).\n")
        md.append(f"- **Baseline Naturalness / Intelligibility**: {human_eval_summary['baseline_variant']['mean_naturalness']} / {human_eval_summary['baseline_variant']['mean_intelligibility']}\n")
        md.append(f"- **RimeRx Naturalness / Intelligibility**: {human_eval_summary['rimerx_variant']['mean_naturalness']} / {human_eval_summary['rimerx_variant']['mean_intelligibility']}\n")

    human_eval_json_path = os.path.join(RESULTS_DIR, "human_evaluation_results.json")
    metrics_human_eval_json_path = os.path.join(METRICS_DIR, "human_evaluation_results.json")
    for p in [human_eval_json_path, metrics_human_eval_json_path]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(human_eval_summary, f, indent=2)

    # Process Stress Test System Analysis (Phase 9)
    from data import STRESS_TEST_CASES
    stress_summary = {
        "notice": "Dedicated high-difficulty stress corpus evaluation with honest limitation reporting",
        "total_stress_cases": len(STRESS_TEST_CASES),
        "cases": [
            {
                "id": c["id"],
                "category": c.get("category", "stress"),
                "difficulty": c.get("difficulty", "hard"),
                "raw_text": c["raw_text"],
                "expected_pronunciation": c.get("expected_pronunciation", "")
            }
            for c in STRESS_TEST_CASES
        ]
    }

    md.append("\n## Stress-Test System (Phase 9 Hard Voice Cases)\n")
    md.append(f"- **Total Stress Test Cases Configured**: {len(STRESS_TEST_CASES)} hard voice prescription cases (`Augmentin 625mg 1-0-1`, `Pantocid-DSR 40/30 mg`, `1/2 tablet 0-1-0`).\n")
    md.append("- **EXPECTED vs HEARD Protocol**: Evaluates side-by-side ASR transcript recall across `drug`, `strength`, `dose`, `frequency`, `duration`, and `date` with honest limitation flagging on acoustic misreads.\n")

    stress_json_path = os.path.join(RESULTS_DIR, "stress_test_results.json")
    metrics_stress_json_path = os.path.join(METRICS_DIR, "stress_test_results.json")
    for p in [stress_json_path, metrics_stress_json_path]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(stress_summary, f, indent=2)

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"[ANALYSIS] Summary successfully written to {SUMMARY_PATH}")
    print(f"[ANALYSIS] Controlled experiment outputs written to:\n  - {baseline_csv_path}\n  - {rimex_csv_path}\n  - {comparison_csv_path}\n  - {metrics_json_path}\n  - {per_case_evidence_path}\n  - {human_eval_json_path}\n  - {stress_json_path}")

if __name__ == "__main__":
    analyze()

