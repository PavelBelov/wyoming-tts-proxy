from abc import ABC, abstractmethod


class ISynthesizer(ABC):

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Синхронный синтез текста в WAV (bytes)."""
        raise NotImplementedError
