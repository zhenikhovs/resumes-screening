# Новый pipeline ранжирования

Описание pipeline: фильтр по опыту → similarity → итоговый score → порог → top-K.

**Текст для диссертации:** [DISSERTATION_RANKING.md](DISSERTATION_RANKING.md).

## Шаги pipeline

1. **Фильтр в пул (жёсткий)**  
   Кандидат допускается к similarity, если  
   `resume_experience_months >= 0.8 * vacancy_min_experience_months`.  
   Остальные исключаются.

2. **Признак experience_match (для score)**  
   Среди допущенных в пул:
   - `experience_match = 1`, если `resume_experience_months >= vacancy_min_experience_months` (полный минимум вакансии, **без** 0.8);
   - `experience_match = 0`, если прошёл только мягкий порог 0.8×min, но стаж ниже полного min.

3. **Similarity**
   - **Classical:** BM25 / TF-IDF по полям classical (полный лемматизированный опыт). Тексты **без** `append_experience_*`.
   - **Transformer:** эмбеддинги по короткому полю `text` (+ месяцы стажа словами при encode). **Без** полного опыта за всю карьеру.

4. **Итоговый score**  
   `final_score = 0.9 * similarity_score + 0.1 * experience_match`

5. **Нормализация** — min-max по кандидатам одной вакансии → `score_norm` ∈ [0, 1].

6. **Порог** — 90-й перцентиль `score_norm` по вакансии.

7. **Top-K** — до 10 кандидатов с `score_norm >= threshold`.

## Входные данные

- **Classical:** `data/prepared/.../cleaned/classical/`
- **Transformer:** `data/prepared/.../cleaned/transformer/` — поля `text` (би-encoder), `text_rerank` (cross-encoder, чуть больше опыта)

## Запуск

```bash
python run.py clean
python run.py pipeline_ranking
python run.py pipeline_ranking --transformer --transformer-method minilm   # и др.
python run.py pipeline_rerank --transformer-method e5 --model russian
```

Отчёты: `python scripts/build_ranking_comparison_report.py`, `python scripts/build_rerank_comparison_report.py`

## Пути результатов

- `data/results/pipeline_classical/`, `data/results/pipeline_transformer/<method>/`
- `data/results/pipeline_stats/`
- `data/results/pipeline_cross_encoder/`

## Конфигурация (`config/pipeline_config.py`)

- `EXPERIENCE_FACTOR = 0.8` — порог входа в пул
- `SIMILARITY_WEIGHT = 0.9`, `EXPERIENCE_MATCH_WEIGHT = 0.1`
- `PERCENTILE_THRESHOLD = 90`, `TOP_K = 10`
- `EMBEDDING_EXPERIENCE_JOBS / EMBEDDING_EXPERIENCE_MAX_CHARS` — усечение опыта в `text`
- `RERANK_EXPERIENCE_JOBS / RERANK_EXPERIENCE_MAX_CHARS` — в `text_rerank`
