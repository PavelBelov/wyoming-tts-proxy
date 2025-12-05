import io
import grpc

from iSynthesizer import ISynthesizer

import yandex.cloud.ai.tts.v3.tts_pb2 as tts_pb2
import yandex.cloud.ai.tts.v3.tts_service_pb2_grpc as tts_service_pb2_grpc


class YandexTTSConfig:
    def __init__(
        self,
        token: str,
        address="tts.api.cloud.yandex.net:443",
        voice="yulduz_ru",
        role="neutral",
        speed=1.2,
    ):
        self.token: str = token
        self.address: str = address
        self.voice: str = voice
        self.role: str = role
        self.speed: float = speed


class YandexSynthesizer(ISynthesizer):
    def __init__(self, cfg: YandexTTSConfig):
        self.cfg = cfg

    def synthesize(self, text: str) -> bytes:
        request = tts_pb2.UtteranceSynthesisRequest(
            text=text,
            output_audio_spec=tts_pb2.AudioFormatOptions(
                container_audio=tts_pb2.ContainerAudio(
                    container_audio_type=tts_pb2.ContainerAudio.WAV
                )
            ),
            hints=[
                tts_pb2.Hints(voice=self.cfg.voice),
                tts_pb2.Hints(role=self.cfg.role),
                tts_pb2.Hints(speed=self.cfg.speed),
            ],
            loudness_normalization_type=tts_pb2.UtteranceSynthesisRequest.LUFS,
        )

        # Установите соединение с сервером.
        cred = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(self.cfg.address, cred)
        try:
            stub = tts_service_pb2_grpc.SynthesizerStub(channel)

            # Отправьте данные для синтеза.
            it = stub.UtteranceSynthesis(
                request,
                metadata=(
                    # Параметры для аутентификации с IAM-токеном
                    ("authorization", f"Bearer {self.cfg.token}"),
                    # Параметры для аутентификации с API-ключом от имени сервисного аккаунта
                    # ('authorization', f'Api-Key {api_key}'),
                ),
            )

            # Соберите аудиозапись по порциям.

            audio = io.BytesIO()
            for response in it:
                audio.write(response.audio_chunk.data)
            audio.seek(0)
            return audio.getvalue()
        finally:
            channel.close()
