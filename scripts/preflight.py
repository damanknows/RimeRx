#!/usr/bin/env python
"""
RimeRx Preflight Check Script
Verifies environment variables, configuration alignment, and live Rime TTS API connectivity.
"""
import os
import sys
import time
import httpx
from dotenv import load_dotenv

# Ensure repository root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from config.rime import RIME_MODEL, RIME_SPEAKER, RIME_ENDPOINT, RIME_AUDIO_FORMAT, RIME_LANGUAGE, verify_rime_configuration

def run_preflight() -> bool:
    print("=" * 76)
    print("                RIMERX PREFLIGHT VERIFICATION RUNNER")
    print("=" * 76)

    results = []
    all_passed = True

    # Check 1: RIME_API_KEY
    api_key = os.getenv("RIME_API_KEY", "").strip()
    if not api_key or api_key == "your_rime_api_key_here":
        results.append({
            "check": "RIME_API_KEY",
            "target": "Present & non-empty",
            "status": "FAIL",
            "details": "Missing or placeholder in .env"
        })
        all_passed = False
    else:
        masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        results.append({
            "check": "RIME_API_KEY",
            "target": "Present & non-empty",
            "status": "PASS",
            "details": f"Configured ({masked}, len={len(api_key)})"
        })

    # Check 2: RIME_MODEL matches config module
    env_model = os.getenv("RIME_MODEL", "").strip()
    expected_model = "mistv3"
    if env_model and not env_model.startswith("your_") and env_model != RIME_MODEL:
        results.append({
            "check": "RIME_MODEL Alignment",
            "target": expected_model,
            "status": "FAIL",
            "details": f"Env '{env_model}' != config '{RIME_MODEL}'"
        })
        all_passed = False
    elif RIME_MODEL != expected_model:
        results.append({
            "check": "RIME_MODEL Alignment",
            "target": expected_model,
            "status": "FAIL",
            "details": f"Config has '{RIME_MODEL}', expected '{expected_model}'"
        })
        all_passed = False
    else:
        results.append({
            "check": "RIME_MODEL Alignment",
            "target": expected_model,
            "status": "PASS",
            "details": f"Verified config value '{RIME_MODEL}'"
        })

    # Check 3: RIME_SPEAKER matches config module
    env_speaker = os.getenv("RIME_SPEAKER", "").strip()
    expected_speaker = "sirius"
    if env_speaker and not env_speaker.startswith("your_") and env_speaker != RIME_SPEAKER:
        results.append({
            "check": "RIME_SPEAKER Alignment",
            "target": expected_speaker,
            "status": "FAIL",
            "details": f"Env '{env_speaker}' != config '{RIME_SPEAKER}'"
        })
        all_passed = False
    elif RIME_SPEAKER != expected_speaker:
        results.append({
            "check": "RIME_SPEAKER Alignment",
            "target": expected_speaker,
            "status": "FAIL",
            "details": f"Config has '{RIME_SPEAKER}', expected '{expected_speaker}'"
        })
        all_passed = False
    else:
        results.append({
            "check": "RIME_SPEAKER Alignment",
            "target": expected_speaker,
            "status": "PASS",
            "details": f"Verified config value '{RIME_SPEAKER}'"
        })

    # Check 4: Live Rime Production Catalog Verification
    if not api_key or api_key == "your_rime_api_key_here":
        results.append({
            "check": "Live Catalog Verification",
            "target": "HTTP 200 + active in catalog",
            "status": "SKIP",
            "details": "Skipped because RIME_API_KEY is not set"
        })
        all_passed = False
    else:
        is_valid, v_msg = verify_rime_configuration(
            api_key=api_key,
            model=RIME_MODEL,
            speaker=RIME_SPEAKER,
            lang=RIME_LANGUAGE,
            endpoint=RIME_ENDPOINT,
            audio_format=RIME_AUDIO_FORMAT,
            raise_on_failure=False,
        )
        if is_valid:
            results.append({
                "check": "Live Catalog Verification",
                "target": f"{RIME_MODEL}/{RIME_SPEAKER}/{RIME_LANGUAGE}",
                "status": "PASS",
                "details": "Confirmed active in Rime production catalog"
            })
        else:
            results.append({
                "check": "Live Catalog Verification",
                "target": f"{RIME_MODEL}/{RIME_SPEAKER}/{RIME_LANGUAGE}",
                "status": "FAIL",
                "details": v_msg
            })
            all_passed = False

    # Print Formatted PASS/FAIL Table
    print(f"{'CHECK':<28} | {'TARGET':<22} | {'STATUS':<6} | {'DETAILS'}")
    print("-" * 28 + "-+-" + "-" * 22 + "-+-" + "-" * 6 + "-+-" + "-" * 32)
    for r in results:
        status_str = f"\033[92m{r['status']}\033[0m" if r['status'] == 'PASS' else f"\033[91m{r['status']}\033[0m"
        # Fallback for non-ANSI terminals:
        plain_status = r['status']
        print(f"{r['check']:<28} | {r['target']:<22} | {plain_status:<6} | {r['details']}")

    print("=" * 76)
    if all_passed:
        print("PREFLIGHT RESULT: ALL CHECKS PASSED (Ready for Evaluation & Benchmarking)")
        print("=" * 76)
        return True
    else:
        print("PREFLIGHT RESULT: FAILED - One or more preflight requirements not satisfied.")
        print("=" * 76)
        return False

if __name__ == "__main__":
    success = run_preflight()
    sys.exit(0 if success else 1)
