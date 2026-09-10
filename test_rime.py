import os, httpx
from dotenv import load_dotenv

load_dotenv()
RIME_API_KEY = os.getenv("RIME_API_KEY")
RIME_URL = os.getenv("RIME_URL", "https://users.rime.ai/v1/rime-tts")

HEADERS = {
    "Authorization": f"Bearer {RIME_API_KEY or ''}",
    "Content-Type": "application/json",
    "Accept": "audio/mp3"
}


def test_speakers():
    if not RIME_API_KEY:
        print("[RIME TEST] RIME_API_KEY not set; skipping live test.")
        return None
    speakers = ["abbey", "allison", "celeste", "kendall", "marsh", "rex", "marissa", "ava", "logan"]

    
    for spk in speakers:
        payload = {
            "speaker": spk,
            "text": "Tablet Augmentin six two five milligram. Doctor Reddys Lab.",
            "audioFormat": "mp3"
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(RIME_URL, json=payload, headers=HEADERS)
                print(f"[RIME TEST] Speaker '{spk}' -> Status {resp.status_code}")
                if resp.status_code == 200:
                    os.makedirs("static/audio", exist_ok=True)
                    with open("static/audio/test_rime.mp3", "wb") as f:
                        f.write(resp.content)
                    print(f"SUCCESS! Audio generated using speaker '{spk}' ({len(resp.content)} bytes)")
                    return spk
                else:
                    print(f"  Response: {resp.text[:150]}")
        except Exception as e:
            print(f"  Exception: {e}")
    return None

if __name__ == "__main__":
    test_speakers()
