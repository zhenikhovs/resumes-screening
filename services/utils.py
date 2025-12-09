import json
import os
import logging


def load_json(path):
    """Загружает JSON файл, возвращает пустой список, если файла нет"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    """Сохраняет данные в JSON файл"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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