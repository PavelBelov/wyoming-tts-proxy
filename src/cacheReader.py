import os
import json
import threading
import uuid
import logging
import requests
from pathlib import Path
from iSynthesizer import ISynthesizer

logger = logging.getLogger(__name__)


def _load_map(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        logger.exception("Failed to load json map from %s", path)
        return {}


def _get_file_data(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


class CacheReader:
    def __init__(self, synthesizer: ISynthesizer, webhook: str, path_root="data"):
        self.synthesizer: ISynthesizer = synthesizer
        self.__wenhook: str = webhook
        self.__sync = threading.Lock()

        cfg_data = "_data.json"

        self.__path_predefined: str = os.path.join(path_root, "def")
        self.__path_cache: str = os.path.join(path_root, "cache")

        os.makedirs(self.__path_predefined, exist_ok=True)
        os.makedirs(self.__path_cache, exist_ok=True)

        self.__path_cache_data: str = os.path.join(self.__path_cache, cfg_data)

        self.__items_predefined: dict[str, str] = _load_map(
            os.path.join(self.__path_predefined, cfg_data)
        )
        self.__items_cache: dict[str, str] = _load_map(self.__path_cache_data)

    def _get(self, text: str):
        with self.__sync:
            if text in self.__items_cache:
                return
            try:
                newData = self.synthesizer.synthesize(text)
                if newData is not None:
                    fileNameShort = str(uuid.uuid4()) + ".wav"
                    fileNameFull = os.path.join(self.__path_cache, fileNameShort)
                    with open(fileNameFull, "xb") as f:
                        f.write(newData)
                    self.__items_cache[text] = fileNameShort
                    with open(self.__path_cache_data, "w", encoding="utf-8") as f:
                        json.dump(self.__items_cache, f, ensure_ascii=False, indent=2)
                    logger.info(
                        "Added new cache item for text=%r -> %s", text, fileNameShort
                    )
                    if self.__wenhook:
                        requests.post(
                            self.__wenhook,
                            data=json.dumps({}),
                            headers={"Content-Type": "application/json"},
                        )

            except Exception:
                logger.exception("Error while generating cache for text=%r", text)
                return

    def get(self, text: str) -> bytes | None:
        itemName = self.__items_predefined.get(text, None)
        if itemName is not None:
            return _get_file_data(os.path.join(self.__path_predefined, itemName))

        itemName = self.__items_cache.get(text, None)
        if itemName is not None:
            return _get_file_data(os.path.join(self.__path_cache, itemName))

        thread = threading.Thread(target=self._get, args=(text,), daemon=True)
        thread.start()

        return None
