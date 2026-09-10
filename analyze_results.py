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

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"[ANALYSIS] Summary successfully written to {SUMMARY_PATH}")

if __name__ == "__main__":
    analyze()
