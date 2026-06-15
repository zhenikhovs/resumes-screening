# Разметка по топ-k (без ручной разметки и логов)

Разметка строится автоматически по результатам ранжирования: **топ-k кандидатов по каждой вакансии считаем релевантными (1), остальных — 0.**

Обоснование: задаём порог отсечки — «столько кандидатов мы рассматриваем как релевантных» для экспериментов и сравнения методов.

---

## Настройки

В **`config/labels_config.py`**:

- **`LABELS_TOP_K`** — сколько кандидатов в голове списка считать релевантными (по умолчанию 5).
- **`LABELS_TOP_K_OPTIONS`** — варианты для экспериментов (например 5, 10, 20).
- **`LABELS_SOURCE_METHOD`** — метод, по результатам которого строим разметку (по умолчанию `bm25`).

---

## Как пользоваться

### 1. Получить результаты ранжирования

Сначала нужно иметь результаты хотя бы одного метода (например BM25):

```bash
python run.py clean    # если ещё не сделано
python run.py rank --method bm25
```

Файлы появятся в `data/results/bm25_results/`.

### 2. Сгенерировать разметку по топ-k

```bash
python -m services.evaluation.build_labels_from_ranking --method bm25 --top-k 5
```

По умолчанию создаётся файл `data/labels/top_k_bm25_k5.json` (список пар `vacancy_id`, `resume_id`, `relevance`).

Другие варианты:

```bash
# Топ-20
python -m services.evaluation.build_labels_from_ranking --method bm25 --top-k 20

# Взять за основу TF-IDF
python -m services.evaluation.build_labels_from_ranking --method tfidf --top-k 10 --output data/labels/top_k_tfidf_k10.json
```

### 3. Оценить другой метод по этой разметке

Разметка построена по BM25 (топ-5). Теперь можно посчитать NDCG/MAP/MRR для другого метода, например TF-IDF:

```bash
python -m services.evaluation.evaluate_ranking --labels data/labels/top_k_bm25_k5.json --method tfidf --k 5 10
```

Так можно сравнить методы: один задаёт «эталон» (топ-k = релевантные), остальные оцениваются по тому, насколько хорошо они поднимают этих же кандидатов вверх.

---

## Формат файла разметки

JSON — список объектов:

```json
[
  { "vacancy_id": "123", "resume_id": "456", "relevance": 1 },
  { "vacancy_id": "123", "resume_id": "789", "relevance": 0 }
]
```

Один файл можно использовать и для оценки (evaluate_ranking), и позже для обучения LTR.
