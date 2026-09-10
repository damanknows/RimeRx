import os, sys, csv, json, asyncio, argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import RESULTS_DIR, RIME_API_KEY
from app.data import TEST_CASES, tune_for_rime, extract_critical_entities
from app.tts.providers import get_provider
from app.asr import transcribe_audio, verify_critical_entities, EVAL_BEAM_SIZE
from app.main import text_to_phonemes, analyze_word_errors
import jiwer

def check_credentials():
    rime_key = os.getenv("RIME_API_KEY", RIME_API_KEY)
    if not rime_key or rime_key == "your_rime_api_key_here":
        print("\n" + "=" * 60)
        print("ERROR: RIME_API_KEY environment variable is missing or empty!")
        print("Please set a valid RIME_API_KEY in your .env file or environment.")
        print("Example: export RIME_API_KEY='your_api_key_here'")
        print("=" * 60 + "\n")
        sys.exit(1)

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

        for case in cases:
            case_id = case["id"]
            raw_text = case["raw_text"]
            expected = case["expected_pronunciation"]

            for provider_name in providers:
                try:
                    p = get_provider(provider_name)
                except Exception as e:
                    print(f"Skipping provider {provider_name}: {e}")
                    continue

                for variant in variants:
                    prompt = raw_text if variant == "default" else tune_for_rime(raw_text)
                    per = compute_per(prompt, expected)

                    try:
                        audio_bytes, meta = await p.synthesize(prompt)
                        dest_dir = CLIPS_RIMEX_DIR if variant == "tuned" else CLIPS_BASELINE_DIR
                        fname = f"{case_id}_{provider_name}_{variant}.mp3"
                        fpath = os.path.join(dest_dir, fname)

                        with open(fpath, "wb") as audio_f:
                            audio_f.write(audio_bytes)

                        hypothesis = transcribe_audio(fpath, beam_size=EVAL_BEAM_SIZE)

                        txt_dir = TRANSCRIPTS_RIMEX_DIR if variant == "tuned" else TRANSCRIPTS_BASELINE_DIR
                        txt_path = os.path.join(txt_dir, f"{case_id}_{provider_name}_{variant}.txt")
                        with open(txt_path, "w", encoding="utf-8") as txt_f:
                            txt_f.write(hypothesis)

                        wer_val, _ = analyze_word_errors(expected, hypothesis)

                        raw_entities = extract_critical_entities(raw_text)
                        ent_ver = verify_critical_entities(raw_entities, hypothesis)
                        entity_acc = ent_ver["critical_token_acc"]

                        row = {
                            "case_id": case_id,
                            "domain": case.get("domain", ""),
                            "category": case.get("category", ""),
                            "provider": provider_name,
                            "variant": variant,
                            "raw_text": raw_text,
                            "prompt_used": prompt,
                            "expected_pronunciation": expected,
                            "hypothesis": hypothesis,
                            "wer": wer_val,
                            "per": per,
                            "entity_acc": entity_acc,
                            "ttfb_ms": meta.get("ttfb_ms", 0),
                            "total_ms": meta.get("total_ms", 0),
                            "cold": meta.get("cold", False),
                            "status": "SUCCESS"
                        }
                        writer.writerow(row)
                        writer_m.writerow(row)
                        print(f"[{provider_name.upper()} | {variant}] {case_id} => WER: {wer_val}%, PER: {per}%, Entity Acc: {entity_acc}%")

                    except Exception as err:
                        print(f"FAILED [{provider_name} | {variant}] {case_id}: {err}")
                        row = {
                            "case_id": case_id,
                            "domain": case.get("domain", ""),
                            "category": case.get("category", ""),
                            "provider": provider_name,
                            "variant": variant,
                            "raw_text": raw_text,
                            "prompt_used": prompt,
                            "expected_pronunciation": expected,
                            "hypothesis": "",
                            "wer": 100.0,
                            "per": per,
                            "entity_acc": 0.0,
                            "ttfb_ms": 0,
                            "total_ms": 0,
                            "cold": False,
                            "status": f"FAILED: {err}"
                        }
                        writer.writerow(row)
                        writer_m.writerow(row)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RimeRx benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases to run")
    args = parser.parse_args()

    check_credentials()
    asyncio.run(run_benchmark(limit=args.limit))
