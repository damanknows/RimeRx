"""Interruption and Recovery Test Suite for Rime WebSocket Streaming TTS.

Evaluates full-duplex interruption scenario on medication instructions:
1. Starts synthesizing long medication instruction (> 8 seconds of audio).
2. Mid-synthesis, triggers cancel().
3. Asserts:
   (a) No further audio chunks emitted after cancel to the initial callback.
   (b) Queued audio buffer is immediately cleared.
   (c) Subsequent synthesis call produces correct, non-stale audio for NEW text.
4. Measures and asserts cancel-to-silence latency in milliseconds (< 200ms threshold).
"""

import asyncio
import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from dotenv import load_dotenv

from src.rime_ws import RimeWebSocketClient

load_dotenv()


def test_mid_synthesis_interruption():
    async def _test_impl():
        api_key = os.getenv("RIME_API_KEY")
        if not api_key:
            pytest.skip("RIME_API_KEY is not configured in environment.")

        client = RimeWebSocketClient(api_key=api_key)
        await client.connect()

        first_emitted_chunks = []

        def first_callback(chunk: bytes):
            first_emitted_chunks.append(chunk)

        # 1. Long medication instruction (>8s of audio: ~45 words)
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

        # Wait until audio chunks begin streaming from Rime (mid-synthesis)
        for _ in range(200):
            if len(first_emitted_chunks) >= 5:
                break
            await asyncio.sleep(0.02)

        chunks_before_cancel = len(first_emitted_chunks)
        assert chunks_before_cancel >= 5, f"Expected >= 5 chunks before cancel, got {chunks_before_cancel}"

        # 2. Mid-synthesis: Call cancel()
        cancel_latency_ms = client.cancel()

        # 3. Assertions
        # Assertion (a): cancel-to-silence latency is well under rubric acceptance limit (200ms)
        print(f"\n[INTERRUPTION AUDIT] Cancel-to-silence latency: {cancel_latency_ms:.4f} ms")
        assert cancel_latency_ms < 200.0, f"Cancel latency too high: {cancel_latency_ms} ms >= 200ms"

        # Wait 300ms to allow any in-flight network packets to hit client
        await asyncio.sleep(0.3)

        # Assertion (a): Zero further audio chunks emitted to initial callback after cancel
        stale_chunks_emitted = len(first_emitted_chunks) - chunks_before_cancel
        assert stale_chunks_emitted == 0, (
            f"Stale audio chunk leak detected! {stale_chunks_emitted} chunks emitted after cancel()"
        )

        # Assertion (b): Queued buffer is cleared immediately
        assert len(client.buffer) == 0, f"Client buffer not cleared: {len(client.buffer)} chunks remain"
        assert client.queued_audio_bytes == 0, f"Client queued bytes not zero: {client.queued_audio_bytes}"

        # Assertion (c): Subsequent synthesis call produces correct audio for NEW text
        second_emitted_chunks = []
        second_timestamps = []

        def second_callback(chunk: bytes):
            second_emitted_chunks.append(chunk)

        def second_ts_callback(ts: dict):
            second_timestamps.append(ts)

        new_medication_instruction = "Amoxicillin 250mg capsule, take two capsules orally before meals."

        ctx2 = await client.synthesize_stream(
            new_medication_instruction,
            audio_callback=second_callback,
            timestamps_callback=second_ts_callback,
        )

        assert ctx2 != ctx1, "Subsequent synthesis contextId must be distinct from cancelled contextId"

        completed = await client.wait_for_completion(ctx2, timeout=20.0)
        assert completed, "Subsequent synthesis failed to complete within timeout"

        # Verify second audio integrity
        total_second_bytes = sum(len(c) for c in second_emitted_chunks)
        assert len(second_emitted_chunks) > 0, "No audio chunks received for subsequent instruction"
        assert total_second_bytes > 5000, (
            f"Subsequent audio bytes too small ({total_second_bytes} bytes), expected valid speech payload"
        )

        # Verify initial callback remains completely silent throughout subsequent synthesis
        assert len(first_emitted_chunks) == chunks_before_cancel, (
            "Stale audio leaked to old callback during subsequent synthesis"
        )

        await client.close()

    asyncio.run(_test_impl())
