""""Verify RimeRx model, speaker, and language configuration against Rime's live production catalog.

Fails loudly ([CONFIG ERROR] with non-zero exit) if the configured combination is rejected.
"""

import os
import sys

# Ensure repository root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from config.rime import (
    RIME_AUDIO_FORMAT,
    RIME_ENDPOINT,
    RIME_LANGUAGE,
    RIME_MODEL,
    RIME_SPEAKER,
    verify_rime_configuration,
)


def main():
    print("=" * 78)
    print("        RimeRx Live Production Catalog Configuration Verifier")
    print("=" * 78)
    print(f"Target Model:    {RIME_MODEL}")
    print(f"Target Speaker:  {RIME_SPEAKER}")
    print(f"Target Language: {RIME_LANGUAGE}")
    print(f"Target Format:   {RIME_AUDIO_FORMAT}")
    print(f"Target Endpoint: {RIME_ENDPOINT}\n")

    api_key = os.getenv("RIME_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        print("[CONFIG ERROR] RIME_API_KEY environment variable is not configured.", file=sys.stderr)
        sys.exit(1)

    print("[INFO] Verifying against Rime's live production API...")
    is_valid, msg = verify_rime_configuration(
        api_key=api_key,
        model=RIME_MODEL,
        speaker=RIME_SPEAKER,
        lang=RIME_LANGUAGE,
        endpoint=RIME_ENDPOINT,
        audio_format=RIME_AUDIO_FORMAT,
        raise_on_failure=False,
    )

    if is_valid:
        print(f"\n{msg}")
        print("=" * 78)
        print("[SUCCESS] Production catalog configuration is 100% valid and operational.")
        print("=" * 78)
        sys.exit(0)
    else:
        print(f"\n{msg}", file=sys.stderr)
        print("=" * 78, file=sys.stderr)
        print("[CONFIG ERROR] Startup/Preflight verification FAILED.", file=sys.stderr)
        print("=" * 78, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
