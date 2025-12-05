import os
import asyncio
import json
from functools import partial
import logging

from cacheReader import CacheReader
from yandexTTS import YandexTTSConfig, YandexSynthesizer
from ttsProxy import TtsProxyHandler

from wyoming.server import AsyncServer


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    with open(os.path.join("data", "config.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    yandex_cfg = YandexTTSConfig(**data["yandex"])
    endpoint = data["endpoint"]
    parentEndpoint = data["parent"]
    webhook = data["webhook"]

    yandexTTS = YandexSynthesizer(yandex_cfg)
    cacheReader = CacheReader(yandexTTS, webhook)

    server = AsyncServer.from_uri(endpoint)
    logger.info("Starting")
    await server.run(partial(TtsProxyHandler, parentEndpoint, cacheReader))


if __name__ == "__main__":
    asyncio.run(run())
