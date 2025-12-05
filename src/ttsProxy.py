import io
import wave
import logging

from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.server import AsyncEventHandler
from wyoming.tts import (
    Synthesize,
    SynthesizeStart,
    SynthesizeChunk,
    SynthesizeStop,
    SynthesizeStopped,
)
from wyoming.client import AsyncClient
from wyoming.event import Event
from wyoming.info import Describe, Info

from cacheReader import CacheReader

logger = logging.getLogger(__name__)


class TtsProxyHandler(AsyncEventHandler):
    def __init__(self, parentUri: str, cacheReader: CacheReader, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parentUri: str = parentUri
        self._cacheReader: CacheReader = cacheReader
        self._stream_text: str | None = None

    async def _proxy_to_parent(self, synth: Synthesize) -> None:
        async with AsyncClient.from_uri(self._parentUri) as client:
            await client.write_event(synth.event())
            event = await client.read_event()
            while event is not None:
                await self.write_event(event)
                if AudioStop.is_type(event.type):
                    return
                event = await client.read_event()

    async def _proxy_describe(self) -> None:
        async with AsyncClient.from_uri(self._parentUri) as client:
            await client.write_event(Describe().event())
            event = await client.read_event()
            while event is not None:
                await self.write_event(event)
                if Info.is_type(event.type):
                    return
                event = await client.read_event()

    async def _send_wav(self, data: bytes) -> None:
        with wave.open(io.BytesIO(data)) as wf:
            rate = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()

            await self.write_event(
                AudioStart(rate=rate, width=width, channels=channels).event()
            )
            frames = wf.readframes(1024)
            while frames:
                await self.write_event(
                    AudioChunk(
                        rate=rate, width=width, channels=channels, audio=frames
                    ).event()
                )
                frames = wf.readframes(1024)
            await self.write_event(AudioStop().event())

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self._proxy_describe()
            return True

        if Synthesize.is_type(event.type):
            synth = Synthesize.from_event(event)
            text = synth.text.strip()
            if text == self._stream_text:
                return True
            fromCache = self._cacheReader.get(text)
            if fromCache is not None:
                await self._send_wav(fromCache)
            else:
                await self._proxy_to_parent(synth)
            return True

        if SynthesizeStart.is_type(event.type):
            self._stream_text = ""
            return True
        if SynthesizeChunk.is_type(event.type):
            chunk = SynthesizeChunk.from_event(event)
            if self._stream_text is None:
                self._stream_text = ""
            self._stream_text += chunk.text
            return True
        if SynthesizeStop.is_type(event.type):
            text = (self._stream_text or "").strip()
            self._stream_text = None
            fromCache = self._cacheReader.get(text)
            if fromCache is not None:
                await self._send_wav(fromCache)
            else:
                await self._proxy_to_parent(Synthesize(text))

            await self.write_event(SynthesizeStopped().event())
            return True

        logger.warning("not handled %s", event.type)
        return True
