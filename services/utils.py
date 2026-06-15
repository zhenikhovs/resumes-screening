import json
import os
import logging
from pathlib import Path
from typing import Any, Union


def load_json(path: Union[str, Path]) -> Any:
    """Загружает JSON из файла. При отсутствии файла возвращает пустой список."""
    path = Path(path) if not isinstance(path, (str, bytes)) else path
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path: Union[str, Path], data: Any) -> None:
    """Сохраняет данные в JSON файл."""
    path = Path(path) if not isinstance(path, (str, bytes)) else path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_get(data: dict, key: str, default: Any = "") -> Any:
    """Безопасное получение значения из словаря (None заменяется на default)."""
    value = data.get(key)
    return value if value is not None else default

def setup_logger(
    log_file: str = "log.log",
    level=logging.INFO,
    mode: str = "a"
):
    """
    Настраивает логирование:
    - log_file: путь к файлу лога
    - level: уровень логирования
    - mode: режим открытия файла ('a' или 'w')
    """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=level,
        filename=log_file,
        filemode=mode,
        format="%(asctime)s %(levelname)s:%(message)s"
    )
    return logging