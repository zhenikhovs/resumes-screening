# Факт: использованные модели (идентификаторы Hugging Face)

## Первый этап — плотные эмбеддинги (sentence-transformers)

Задано в `services/ranking/pipeline_transformer.py`, словарь `TRANSFORMER_MODELS`:

| Ключ в коде | Модель |
|-------------|--------|
| e5 | `intfloat/multilingual-e5-large` |
| minilm | `sentence-transformers/all-MiniLM-L6-v2` |
| ru_sbert | `ai-forever/sbert_large_nlu_ru` |
| mpnet | `all-mpnet-base-v2` |

Для E5 входы кодируются с префиксами `query:` / `passage:` (см. `FACT_ALGORITHM_FIRST_STAGE.md`).

---

## Второй этап — cross-encoder

Задано в `services/ranking/cross_encoder_rerank.py` (и те же имена для classical-rerank), словарь `CROSS_ENCODER_MODELS`:

| Ключ | Модель |
|------|--------|
| russian | `DiTy/cross-encoder-russian-msmarco` |
| minilm | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| multilingual | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` |

Пара `(вакансия, резюме)` оценивается одним проходом модели; выход — скаляр `rerank_score` (в коде приводится к `float`).

**Параметр инференса:** размер батча по умолчанию **32** (`DEFAULT_BATCH_SIZE`).

---

## Первый этап — без нейросетей

- **BM25:** библиотека `rank_bm25`, класс `BM25Okapi`.
- **TF-IDF:** `sklearn.feature_extraction.text.TfidfVectorizer`.
