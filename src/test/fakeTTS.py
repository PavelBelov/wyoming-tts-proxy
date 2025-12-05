from iSynthesizer import ISynthesizer
import os


class FakeTTS(ISynthesizer):
    def __init__(self):
        self.path = os.path.join("test", "test.wav")

    def synthesize(self, text: str) -> bytes:
        with open(self.path, "rb") as f:
            return f.read()
