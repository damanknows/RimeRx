"""Rime WebSocket Streaming Client with Interruption Handling.

Connects to Rime's real-time streaming WebSocket endpoint (wss://users-ws.rime.ai/ws3)
for ultra-low latency full-duplex speech synthesis.

Features:
- Streaming synthesis emitting base64-decoded audio chunks via callback.
- Word-level timestamp events via optional timestamps callback.
- Immediate interruption via cancel() which invalidates the active synthesis context,
  discards queued buffers, silences callbacks in < 1ms, and notifies the server.
"""

import asyncio
import base64
import collections
import json
import logging
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

from dotenv import load_dotenv
import websockets

load_dotenv()

from config.rime import (
    RIME_AUDIO_FORMAT,
    RIME_MODEL,
    RIME_SPEAKER,
    RIME_WS_ENDPOINT,
)

logger = logging.getLogger(__name__)


class RimeWebSocketClient:
    """Full-duplex WebSocket TTS client for Rime (/ws3)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        speaker: Optional[str] = None,
        audio_format: Optional[str] = None,
        sampling_rate: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("RIME_API_KEY")
        if not self.api_key:
            raise ValueError("RIME_API_KEY environment variable or parameter is required.")

        self.endpoint = endpoint or RIME_WS_ENDPOINT
        self.model = model or RIME_MODEL
        self.speaker = speaker or RIME_SPEAKER
        # Default to pcm for streaming playback unless specified
        self.audio_format = audio_format or "pcm"
        self.sampling_rate = sampling_rate

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._reader_task: Optional[asyncio.Task] = None

        # Active synthesis context tracking
        self._active_context_id: Optional[str] = None
        self._active_audio_callback: Optional[Callable[[bytes], None]] = None
        self._active_timestamps_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._done_events: Dict[str, asyncio.Event] = {}

        # Interruption and signal-path tracking
        self._buffer: collections.deque = collections.deque()
        self._last_cancel_time: Optional[float] = None
        self._last_cancel_latency_ms: float = 0.0
        self._last_network_chunk_time: Optional[float] = None
        self._cancel_signal_to_last_audio_ms: float = 0.0
        self._stale_audio_dropped_bytes: int = 0
        self._stale_audio_emitted_bytes: int = 0

    @property
    def buffer(self) -> List[bytes]:
        """Return shallow copy of queued audio chunks in buffer."""
        return list(self._buffer)

    @property
    def last_cancel_latency_ms(self) -> float:
        """Return local client callback severance and buffer flush latency in ms."""
        return self._last_cancel_latency_ms

    @property
    def cancel_signal_to_last_audio_ms(self) -> float:
        """Return duration in ms from cancel invocation to the last in-flight network chunk arrival."""
        return self._cancel_signal_to_last_audio_ms

    @property
    def stale_audio_dropped_bytes(self) -> int:
        """Return total in-flight audio bytes received from network after cancel and safely discarded."""
        return self._stale_audio_dropped_bytes

    @property
    def queued_audio_bytes(self) -> int:
        """Return total bytes currently queued in client buffer."""
        return sum(len(chunk) for chunk in self._buffer)

    def _build_url(self) -> str:
        """Construct WebSocket connection URL with query parameters."""
        query_params: Dict[str, Any] = {
            "speaker": self.speaker,
            "modelId": self.model,
            "audioFormat": self.audio_format,
        }
        if self.sampling_rate is not None:
            query_params["samplingRate"] = self.sampling_rate

        qs = urlencode(query_params)
        sep = "&" if "?" in self.endpoint else "?"
        return f"{self.endpoint}{sep}{qs}"

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and open."""
        return self.ws is not None and getattr(self.ws, "state", None) == websockets.protocol.State.OPEN

    async def connect(self) -> None:
        """Establish WebSocket connection to Rime and start background reader."""
        if self.is_connected:
            return

        url = self._build_url()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        logger.debug("Connecting to Rime WebSocket: %s", url)

        self.ws = await websockets.connect(url, additional_headers=headers)
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Continuously receive JSON messages from Rime WebSocket."""
        try:
            async for raw_msg in self.ws:
                try:
                    data = json.loads(raw_msg)
                except Exception:
                    continue

                msg_type = data.get("type")
                ctx_id = data.get("contextId")

                # If this message belongs to a cancelled/stale context or there is no active context
                if ctx_id != self._active_context_id:
                    if msg_type == "chunk":
                        # Raw audio payload arrived from network for an abandoned context
                        payload = data.get("data", "")
                        chunk_len = len(base64.b64decode(payload)) if payload else 0
                        self._stale_audio_dropped_bytes += chunk_len
                        now = time.perf_counter()
                        self._last_network_chunk_time = now
                        if self._last_cancel_time is not None:
                            self._cancel_signal_to_last_audio_ms = (now - self._last_cancel_time) * 1000.0
                    elif msg_type in ("done", "error"):
                        if ctx_id in self._done_events:
                            self._done_events[ctx_id].set()
                    continue

                # Active context handling
                if msg_type == "chunk":
                    raw_b64 = data.get("data", "")
                    chunk_bytes = base64.b64decode(raw_b64)
                    self._buffer.append(chunk_bytes)
                    if self._active_audio_callback:
                        self._active_audio_callback(chunk_bytes)

                elif msg_type == "timestamps":
                    word_timestamps = data.get("word_timestamps", {})
                    if self._active_timestamps_callback:
                        self._active_timestamps_callback(word_timestamps)

                elif msg_type == "done":
                    if ctx_id in self._done_events:
                        self._done_events[ctx_id].set()

                elif msg_type == "error":
                    logger.error("Rime WS error for context %s: %s", ctx_id, data.get("message"))
                    if ctx_id in self._done_events:
                        self._done_events[ctx_id].set()

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("Rime WS reader exited: %s", exc)

    async def synthesize_stream(
        self,
        text: str,
        audio_callback: Optional[Callable[[bytes], None]] = None,
        timestamps_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        context_id: Optional[str] = None,
    ) -> str:
        """Send text to be synthesized over WebSocket.

        Args:
            text: Text to synthesize.
            audio_callback: Callback invoked with decoded audio bytes for each chunk.
            timestamps_callback: Optional callback invoked with word-level timestamps dict:
                                 {'words': [...], 'start': [...], 'end': [...]}.
            context_id: Optional tracking identifier (defaults to uuid4).

        Returns:
            context_id: The context identifier associated with this synthesis turn.
        """
        if not self.is_connected:
            await self.connect()

        ctx_id = context_id or str(uuid.uuid4())
        self._active_context_id = ctx_id
        self._active_audio_callback = audio_callback
        self._active_timestamps_callback = timestamps_callback
        self._done_events[ctx_id] = asyncio.Event()

        req = {"text": text, "contextId": ctx_id}
        await self.ws.send(json.dumps(req))
        return ctx_id

    def cancel(self) -> float:
        """Immediately interrupt synthesis, stop playback callbacks, and discard buffers.

        Returns:
            cancel_latency_ms: Milliseconds elapsed to execute the client cancellation.
        """
        t0 = time.perf_counter()

        # 1. Invalidate active context ID so reader loop drops any subsequent chunks
        abandoned_ctx = self._active_context_id
        self._active_context_id = None

        # 2. Sever user callbacks to achieve zero-leakage to playback
        self._active_audio_callback = None
        self._active_timestamps_callback = None

        # 3. Discard queued audio buffer
        self._buffer.clear()

        # 4. Notify any waiters for abandoned context
        if abandoned_ctx and abandoned_ctx in self._done_events:
            self._done_events[abandoned_ctx].set()

        # 5. Best-effort async notification to Rime server to clear speech queue
        if self.is_connected:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.ws.send(json.dumps({"operation": "clear"})))
            except Exception:
                pass

        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        self._last_cancel_time = t0
        self._last_cancel_latency_ms = latency_ms
        return latency_ms

    async def wait_for_completion(self, context_id: str, timeout: float = 15.0) -> bool:
        """Wait until synthesis for given context_id completes.

        Returns True if completed before timeout, False otherwise.
        """
        if context_id not in self._done_events:
            return True
        try:
            await asyncio.wait_for(self._done_events[context_id].wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def close(self) -> None:
        """Gracefully close background reader and WebSocket connection."""
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None

        if self.ws:
            try:
                if self.is_connected:
                    await self.ws.send(json.dumps({"operation": "eos"}))
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
