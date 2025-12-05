import asyncio
import wave
import sounddevice as sd
import soundfile as sf
import os

from wyoming.tts import Synthesize
from wyoming.client import AsyncClient


class AuddioInfo:
    def __init__(self, rate, width, channels):
        self.rate = rate
        self.width = width
        self.channels = channels
        self.payload = []


wyominUri = input("uri: ")
if wyominUri == "":
    wyominUri = "tcp://127.0.0.1:10200"
    print(wyominUri)


async def _proxy_to_wyoming(synth: Synthesize) -> None:
    async with AsyncClient.from_uri(wyominUri) as client:
        await client.write_event(synth.event())
        event = await client.read_event()
        if event.type != "audio-start":
            return None
        result = AuddioInfo(
            event.data["rate"], event.data["width"], event.data["channels"]
        )
        event = await client.read_event()
        while event.type == "audio-chunk":
            result.payload.append(event.payload)
            event = await client.read_event()
        return result


async def test_server():
    while True:
        text = Synthesize(input("text: "))
        response = await _proxy_to_wyoming(text)
        testFileName = os.path.join("test", "result.wav")
        if not response == None:
            with wave.open(testFileName, "wb") as wav_file:
                wav_file.setnchannels(response.channels)
                wav_file.setsampwidth(response.width)
                wav_file.setframerate(response.rate)
                wav_file.writeframes(b"".join(response.payload))

            data, samplerate = sf.read(testFileName)
            sd.play(data, samplerate)
            sd.wait()


if __name__ == "__main__":
    asyncio.run(test_server())
