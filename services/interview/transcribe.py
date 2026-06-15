"""Распознавание речи (Whisper) → transcript.json."""
import os
import threading
from pathlib import Path
from typing import Any

from config.interview_config import WHISPER_MODEL
from services.utils import save_json

_whisper_models: dict[str, Any] = {}
_whisper_lock = threading.Lock()


def _configure_ssl_for_model_download() -> None:
    """Mac/Python: иначе whisper.load_model падает с CERTIFICATE_VERIFY_FAILED."""
    try:
        import certifi

        ca = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
    except ImportError:
        pass


def get_whisper_model(model_name: str | None = None):
    """Один раз на процесс API: модель остаётся в RAM для всех вопросов."""
    name = model_name or WHISPER_MODEL
    if name in _whisper_models:
        return _whisper_models[name]

    with _whisper_lock:
        if name in _whisper_models:
            return _whisper_models[name]
        try:
            import whisper
        except ImportError as e:
            raise RuntimeError(
                "Установите openai-whisper: pip install openai-whisper"
            ) from e

        _configure_ssl_for_model_download()
        print(f"[*] Загрузка Whisper ({name}) в память (один раз на процесс сервера)...")
        _whisper_models[name] = whisper.load_model(name)
        print(f"[+] Whisper ({name}) готов")
        return _whisper_models[name]


def transcribe_audio(
    audio_path: Path,
    output_json: Path,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Транскрибирует аудио как есть (без подсказок с терминами) → transcript.json."""
    name = model_name or WHISPER_MODEL
    model = get_whisper_model(name)
    print(f"[*] Транскрипция ({name}): {audio_path}")
    result = model.transcribe(str(audio_path), language="ru")

    text = (result.get("text") or "").strip()
    payload = {
        "text": text,
        "language": result.get("language", "ru"),
        "model": name,
        "source_audio": str(audio_path),
    }
    save_json(output_json, payload)
    return payload
