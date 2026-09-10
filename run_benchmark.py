import os, sys, csv, json, asyncio, argparse
sys.path.insert(0, os.path.dirname(__file__))

from data import TEST_CASES, tune_for_rime, extract_critical_entities
from tts.providers import get_provider
from asr import transcribe_audio, verify_critical_entities, EVAL_BEAM_SIZE
import jiwer
from main import analyze_word_errors, text_to_phonemes

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CLIPS_DIR = os.path.join(RESULTS_DIR, "clips")
CLIPS_BASELINE_DIR = os.path.join(CLIPS_DIR, "baseline")
CLIPS_RIMEX_DIR = os.path.join(CLIPS_DIR, "rimex")
TRANSCRIPTS_DIR = os.path.join(RESULTS_DIR, "transcripts")
TRANSCRIPTS_BASELINE_DIR = os.path.join(TRANSCRIPTS_DIR, "baseline")
TRANSCRIPTS_RIMEX_DIR = os.path.join(TRANSCRIPTS_DIR, "rimex")
METRICS_DIR = os.path.join(RESULTS_DIR, "metrics")
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
CSV_PATH = os.path.join(RESULTS_DIR, "item_results.csv")
METRICS_CSV_PATH = os.path.join(METRICS_DIR, "item_results.csv")

for d in [RESULTS_DIR, CLIPS_DIR, CLIPS_BASELINE_DIR, CLIPS_RIMEX_DIR,
          TRANSCRIPTS_DIR, TRANSCRIPTS_BASELINE_DIR, TRANSCRIPTS_RIMEX_DIR,
          METRICS_DIR, FIGURES_DIR]:
    os.makedirs(d, exist_ok=True)

def compute_per(prompt_text: str, expected_text: str) -> float:
    pred_phonemes = text_to_phonemes(prompt_text)
    ref_phonemes = text_to_phonemes(expected_text)
    per_val = jiwer.wer(ref_phonemes, pred_phonemes)
    return round(per_val * 100, 2)

async def run_benchmark(limit: int = None):
    cases = TEST_CASES[:limit] if limit else TEST_CASES
    providers = ["rime", "openai", "elevenlabs"]
    variants = ["default", "tuned"]

    fieldnames = [
        "case_id", "domain", "category", "provider", "variant",
        "raw_text", "prompt_used", "expected_pronunciation",
        "hypothesis", "wer", "per", "entity_acc", "ttfb_ms", "total_ms", "cold", "status"
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f, \
         open(METRICS_CSV_PATH, "w", newline="", encoding="utf-8") as f_m:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer_m = csv.DictWriter(f_m, fieldnames=fieldnames)
        writer.writeheader()
        writer_m.writeheader()

        total_runs = len(cases) * len(providers) * len(variants)
        run_count = 0
        print(f"[BENCHMARK] Starting benchmark execution ({total_runs} total evaluation pairs)...")

        for item in cases:
            case_id = item["id"]
            domain = item.get("domain", "Pharmacy")
            category = item.get("category", "general")
            raw_text = item["raw_text"]
            expected_pron = item["expected_pronunciation"]

            raw_entities = extract_critical_entities(raw_text)

            for p_name in providers:
                provider_instance = get_provider(p_name)
                for variant in variants:
                    run_count += 1
                    variant_folder = "baseline" if variant == "default" else "rimex"
                    prompt_text = raw_text if variant == "default" else tune_for_rime(raw_text)

                    # Flat clip path (legacy compatibility) + nested clip path
                    flat_clip_filename = f"{case_id}_{p_name}_{variant}.mp3"
                    flat_clip_path = os.path.join(CLIPS_DIR, flat_clip_filename)

                    nested_clip_dir = CLIPS_BASELINE_DIR if variant_folder == "baseline" else CLIPS_RIMEX_DIR
                    nested_clip_path = os.path.join(nested_clip_dir, f"{case_id}_{p_name}.mp3")

                    transcript_dir = TRANSCRIPTS_BASELINE_DIR if variant_folder == "baseline" else TRANSCRIPTS_RIMEX_DIR
                    transcript_path = os.path.join(transcript_dir, f"{case_id}_{p_name}.json")

                    print(f"[{run_count}/{total_runs}] Case: {case_id} | Provider: {p_name} | Variant: {variant}...", end=" ", flush=True)

                    per_score = compute_per(prompt_text, expected_pron)

                    try:
                        audio_bytes, meta = await provider_instance.synthesize(prompt_text)
                        
                        with open(flat_clip_path, "wb") as cf:
                            cf.write(audio_bytes)
                        with open(nested_clip_path, "wb") as cf:
                            cf.write(audio_bytes)

                        # Transcribe ASR via small.en (beam size 5)
                        hypothesis = transcribe_audio(flat_clip_path, beam_size=EVAL_BEAM_SIZE)
                        wer_score, _ = analyze_word_errors(expected_pron, hypothesis)
                        
                        entity_res = verify_critical_entities(raw_entities, hypothesis)
                        entity_acc = entity_res["accuracy_pct"]

                        row = {
                            "case_id": case_id,
                            "domain": domain,
                            "category": category,
                            "provider": p_name,
                            "variant": variant,
                            "raw_text": raw_text,
                            "prompt_used": prompt_text,
                            "expected_pronunciation": expected_pron,
                            "hypothesis": hypothesis,
                            "wer": wer_score,
                            "per": per_score,
                            "entity_acc": entity_acc,
                            "ttfb_ms": meta.get("ttfb_ms", 0.0),
                            "total_ms": meta.get("total_ms", 0.0),
                            "cold": meta.get("cold", False),
                            "status": "SUCCESS"
                        }
                        writer.writerow(row)
                        writer_m.writerow(row)
                        f.flush()
                        f_m.flush()

                        # Save itemized transcript evidence JSON
                        transcript_evidence = {
                            "case_id": case_id,
                            "domain": domain,
                            "category": category,
                            "provider": p_name,
                            "variant": variant,
                            "raw_text": raw_text,
                            "normalized_text": prompt_text,
                            "expected_pronunciation": expected_pron,
                            "expected_critical_entities": raw_entities,
                            "rime_configuration": {
                                "model_id": "mist/v1",
                                "voice": "marsh",
                                "language": "en-IN",
                                "audio_format": "mp3"
                            },
                            "audio_clip_path": f"results/clips/{variant_folder}/{case_id}_{p_name}.mp3",
                            "hypothesis": hypothesis,
                            "wer": wer_score,
                            "per": per_score,
                            "critical_token_accuracy": entity_acc,
                            "latency": {
                                "ttfb_ms": meta.get("ttfb_ms", 0.0),
                                "total_ms": meta.get("total_ms", 0.0),
                                "cold": meta.get("cold", False)
                            },
                            "status": "SUCCESS"
                        }
                        with open(transcript_path, "w", encoding="utf-8") as tf:
                            json.dump(transcript_evidence, tf, indent=2)

                        print(f"SUCCESS (WER: {wer_score}%, PER: {per_score}%, EntityAcc: {entity_acc}%, TTFB: {meta.get('ttfb_ms')}ms)")

                    except Exception as e:
                        err_msg = str(e)
                        row = {
                            "case_id": case_id,
                            "domain": domain,
                            "category": category,
                            "provider": p_name,
                            "variant": variant,
                            "raw_text": raw_text,
                            "prompt_used": prompt_text,
                            "expected_pronunciation": expected_pron,
                            "hypothesis": "",
                            "wer": "",
                            "per": per_score,
                            "ttfb_ms": "",
                            "total_ms": "",
                            "cold": "",
                            "status": f"FAILED ({err_msg[:80]})"
                        }
                        writer.writerow(row)
                        writer_m.writerow(row)
                        f.flush()
                        f_m.flush()

                        transcript_evidence = {
                            "case_id": case_id,
                            "domain": domain,
                            "category": category,
                            "provider": p_name,
                            "variant": variant,
                            "raw_text": raw_text,
                            "normalized_text": prompt_text,
                            "expected_pronunciation": expected_pron,
                            "expected_critical_entities": raw_entities,
                            "rime_configuration": {
                                "model_id": "mist/v1",
                                "voice": "marsh",
                                "language": "en-IN",
                                "audio_format": "mp3"
                            },
                            "audio_clip_path": f"results/clips/{variant_folder}/{case_id}_{p_name}.mp3",
                            "hypothesis": "",
                            "wer": None,
                            "per": per_score,
                            "critical_token_accuracy": 0.0,
                            "latency": {},
                            "status": f"FAILED ({err_msg[:80]})"
                        }
                        with open(transcript_path, "w", encoding="utf-8") as tf:
                            json.dump(transcript_evidence, tf, indent=2)

                        print(f"SKIPPED/FAILED ({err_msg[:60]})")

    print(f"\n[BENCHMARK] Completed! Item-level results written to {CSV_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RimeRx TTS Benchmark Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of corpus items to run")
    args = parser.parse_args()

    asyncio.run(run_benchmark(limit=args.limit))
