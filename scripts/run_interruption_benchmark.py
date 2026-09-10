"""Mid-Synthesis Interruption Benchmark for Rime TTS WebSocket API.

Runs 5 independent full-duplex interruption trials:
1. Synthesizes a long Indian medication instruction (>8s duration).
2. Mid-synthesis (after receiving initial chunks), triggers client cancel().
3. Evaluates cancel-to-silence latency in ms and checks for any stale audio bytes.
4. Synthesizes a subsequent new medication instruction to confirm clean recovery.
5. Writes results to `results/interruption_results.csv` with columns:
   run, cancel_latency_ms, stale_audio_bytes_after_cancel, pass_fail
"""

import asyncio
import csv
import os
import sys
import time

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.rime_ws import RimeWebSocketClient

load_dotenv()


async def run_single_interruption_trial(run_id: int) -> dict:
    """Run a single interruption and recovery trial against Rime WebSocket API."""
    api_key = os.getenv("RIME_API_KEY")
    if not api_key:
        raise ValueError("RIME_API_KEY is not set.")

    client = RimeWebSocketClient(api_key=api_key)
    await client.connect()

    first_emitted_chunks = []

    def first_callback(chunk: bytes):
        first_emitted_chunks.append(chunk)

    long_medication_instruction = (
        "Take one tablet of Paracetamol 500mg in the morning after breakfast "
        "with a full glass of water, and ensure you do not exceed 4000mg per day "
        "to avoid acute liver injury. If fever or acute pain persists for more than "
        "three consecutive days, stop taking the medication and consult your primary "
        "care physician immediately."
    )

    ctx1 = await client.synthesize_stream(
        long_medication_instruction,
        audio_callback=first_callback,
    )

    # Wait until audio chunks begin streaming
    for _ in range(250):
        if len(first_emitted_chunks) >= 5:
            break
        await asyncio.sleep(0.02)

    chunks_at_cancel = len(first_emitted_chunks)
    bytes_at_cancel = sum(len(c) for c in first_emitted_chunks)

    # Trigger mid-synthesis cancellation
    client_cutoff_ms = client.cancel()
    buffer_len_at_cancel = len(client.buffer)

    # Monitor WebSocket reader loop to record the full network in-flight chunk drain
    await asyncio.sleep(2.0)

    chunks_after_cancel = len(first_emitted_chunks)
    bytes_after_cancel = sum(len(c) for c in first_emitted_chunks)
    stale_bytes_emitted = bytes_after_cancel - bytes_at_cancel
    network_drain_ms = client.cancel_signal_to_last_audio_ms
    dropped_network_bytes = client.stale_audio_dropped_bytes

    # Verify subsequent synthesis for new medication instruction
    second_emitted_chunks = []

    def second_callback(chunk: bytes):
        second_emitted_chunks.append(chunk)

    new_medication_instruction = "Amoxicillin 250mg capsule, take two capsules orally before meals."
    ctx2 = await client.synthesize_stream(
        new_medication_instruction,
        audio_callback=second_callback,
    )

    completed = await client.wait_for_completion(ctx2, timeout=12.0)
    second_bytes = sum(len(c) for c in second_emitted_chunks)

    await client.close()

    passed = (
        chunks_at_cancel >= 5
        and client_cutoff_ms < 200.0
        and stale_bytes_emitted == 0
        and buffer_len_at_cancel == 0
        and completed
        and second_bytes > 5000
    )

    return {
        "run": run_id,
        "client_cutoff_ms": round(client_cutoff_ms, 3),
        "network_drain_ms": round(network_drain_ms, 1),
        "stale_audio_bytes_emitted": stale_bytes_emitted,
        "stale_network_bytes_dropped": dropped_network_bytes,
        "pass_fail": "PASS" if passed else "FAIL",
        "second_instruction_bytes": second_bytes,
    }


async def main():
    print("=" * 95)
    print("           RimeRx WebSocket Interruption & Recovery Benchmark")
    print("=" * 95)
    print("[INFO] Target WebSocket Endpoint: wss://users-ws.rime.ai/ws3")
    print("[INFO] Metrics Captured:")
    print("       1. Client Cutoff Latency (Callback & Buffer Cutoff to Silence): Local synchronous return.")
    print("       2. Network Drain Latency (Cancel Signal -> Last In-Flight Audio Byte): WAN + server queue drain.")
    print("       3. Stale Audio Bytes Emitted to Audio Playback: Must strictly be 0 bytes.")
    print("[INFO] Executing 5 consecutive mid-synthesis interruption stress runs...\n")

    results = []
    for run_id in range(1, 6):
        print(f"[RUN {run_id}/5] Starting mid-synthesis interruption trial...")
        t0 = time.time()
        trial_result = await run_single_interruption_trial(run_id)
        elapsed = time.time() - t0
        print(
            f"          Done in {elapsed:.2f}s | Client Cutoff: {trial_result['client_cutoff_ms']} ms "
            f"| Network Drain: {trial_result['network_drain_ms']} ms "
            f"| Stale Bytes Emitted: {trial_result['stale_audio_bytes_emitted']} "
            f"| Network Dropped: {trial_result['stale_network_bytes_dropped']} B "
            f"| Status: {trial_result['pass_fail']}"
        )
        results.append(trial_result)
        await asyncio.sleep(0.5)

    # Ensure results directory exists
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, "interruption_results.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "run",
                "client_cutoff_ms",
                "network_drain_ms",
                "stale_audio_bytes_emitted",
                "stale_network_bytes_dropped",
                "pass_fail",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"\n[SUCCESS] Wrote benchmark results to {csv_path}\n")

    # Print summary table
    print("+-----+--------------------+--------------------+---------------------------+-----------+")
    print("| Run | Client Cutoff (ms) | Network Drain (ms) | Stale Audio Bytes Emitted | Pass/Fail |")
    print("+-----+--------------------+--------------------+---------------------------+-----------+")
    for r in results:
        print(
            f"|  {r['run']}  |       {r['client_cutoff_ms']:<12} |       {r['network_drain_ms']:<12} |             {r['stale_audio_bytes_emitted']:<13} |   {r['pass_fail']}    |"
        )
    print("+-----+--------------------+--------------------+---------------------------+-----------+")


if __name__ == "__main__":
    asyncio.run(main())
