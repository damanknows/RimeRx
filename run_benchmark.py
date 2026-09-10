import os, sys, csv, asyncio, argparse
sys.path.insert(0, os.path.dirname(__file__))

from data import TEST_CASES, tune_for_rime
from tts.providers import get_provider
from asr import transcribe_audio, EVAL_BEAM_SIZE
import jiwer
from main import analyze_word_errors, text_to_phonemes

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CLIPS_DIR = os.path.join(RESULTS_DIR, "clips")
CSV_PATH = os.path.join(RESULTS_DIR, "item_results.csv")

os.makedirs(CLIPS_DIR, exist_ok=True)

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
        "hypothesis", "wer", "per", "ttfb_ms", "total_ms", "cold", "status"
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        total_runs = len(cases) * len(providers) * len(variants)
        run_count = 0
        print(f"[BENCHMARK] Starting benchmark execution ({total_runs} total evaluation pairs)...")

        for item in cases:
            case_id = item["id"]
            domain = item.get("domain", "Pharmacy")
            category = item.get("category", "general")
            raw_text = item["raw_text"]
            expected_pron = item["expected_pronunciation"]

            for p_name in providers:
                provider_instance = get_provider(p_name)
                for variant in variants:
                    run_count += 1
                    prompt_text = raw_text if variant == "default" else tune_for_rime(raw_text)
                    clip_filename = f"{case_id}_{p_name}_{variant}.mp3"
                    clip_path = os.path.join(CLIPS_DIR, clip_filename)

                    print(f"[{run_count}/{total_runs}] Case: {case_id} | Provider: {p_name} | Variant: {variant}...", end=" ", flush=True)

                    per_score = compute_per(prompt_text, expected_pron)

                    try:
                        audio_bytes, meta = await provider_instance.synthesize(prompt_text)
                        
                        with open(clip_path, "wb") as cf:
                            cf.write(audio_bytes)

                        # Transcribe ASR via small.en (beam size 5)
                        hypothesis = transcribe_audio(clip_path, beam_size=EVAL_BEAM_SIZE)
                        wer_score, _ = analyze_word_errors(expected_pron, hypothesis)

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
                            "ttfb_ms": meta.get("ttfb_ms", 0.0),
                            "total_ms": meta.get("total_ms", 0.0),
                            "cold": meta.get("cold", False),
                            "status": "SUCCESS"
                        }
                        writer.writerow(row)
                        f.flush()
                        print(f"SUCCESS (WER: {wer_score}%, PER: {per_score}%, TTFB: {meta.get('ttfb_ms')}ms)")

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
                        f.flush()
                        print(f"SKIPPED/FAILED ({err_msg[:60]})")

    print(f"\n[BENCHMARK] Completed! Item-level results written to {CSV_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RimeRx TTS Benchmark Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of corpus items to run")
    args = parser.parse_args()

    asyncio.run(run_benchmark(limit=args.limit))
