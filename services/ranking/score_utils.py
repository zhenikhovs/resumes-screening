"""
Общие функции для подсчёта и нормализации скоров при ранжировании.

Нормализация min-max: всегда по пулу кандидатов **одной вакансии** (per-vacancy).
Не по всем файлам и не глобально — для каждой вакансии свой min/max по её кандидатам.
Так корректно для задачи ранжирования и для метрик NDCG/MAP (одна вакансия = один список).
"""
import numpy as np


def tokenize(text: str) -> list:
    """Простая токенизация для BM25/TF-IDF: lower + split по пробелам."""
    return text.lower().split() if text else []


def normalize_scores(scores) -> list:
    """
    Min-max по переданному набору скоров → [0, 1].
    Вызывается по кандидатам одной вакансии (per-vacancy), не по всем файлам.
    Если все значения одинаковы — 1.0 для ненулевых, 0.0 для нуля.
    """
    arr = np.asarray(scores, dtype=float)
    if arr.size == 0:
        return []
    if np.all(arr == arr.flat[0]):
        return [1.0 if s > 0 else 0.0 for s in arr]
    min_val, max_val = arr.min(), arr.max()
    if max_val == min_val:
        return [1.0 if s > 0 else 0.0 for s in arr]
    return ((arr - min_val) / (max_val - min_val)).tolist()
