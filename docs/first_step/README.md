# Материалы для текста диссертации (этап 1)

| Файл | Содержание |
|------|------------|
| [FACT_ALGORITHM_FIRST_STAGE.md](FACT_ALGORITHM_FIRST_STAGE.md) | Фильтр опыта, BM25/TF-IDF, эмбеддинги, score, порог, top-K |
| [FACT_DATA_DOWNLOAD.md](FACT_DATA_DOWNLOAD.md) | Сбор данных с hh.ru |
| [FACT_DATA_CLEANING.md](FACT_DATA_CLEANING.md) | Pre-clean и clean (classical / transformer) |
| [FACT_MODELS.md](FACT_MODELS.md) | Имена моделей Hugging Face |
| [FACT_SECOND_STAGE_CROSS_ENCODER.md](FACT_SECOND_STAGE_CROSS_ENCODER.md) | Rerank cross-encoder |
| [FACT_MAIN_NUMBERS.md](FACT_MAIN_NUMBERS.md) | Цифры: фильтр по опыту, сжатие данных |
| [FACT_QUALITATIVE_SUMMARY.md](FACT_QUALITATIVE_SUMMARY.md) | Качественные выводы по примерам |
| [../DISSERTATION_RANKING.md](../DISSERTATION_RANKING.md) | **Текст для главы: этап 1 (ранжирование)** |
| [../DISSERTATION_INTERVIEW.md](../DISSERTATION_INTERVIEW.md) | **Текст для главы: этап 2 (интервью)** |
| [DESIGN_STEP2_VIDEO_INTERVIEW.md](DESIGN_STEP2_VIDEO_INTERVIEW.md) | Этап 2: исходный дизайн (до веба) |
| [../INTERVIEW_PIPELINE.md](../INTERVIEW_PIPELINE.md) | Этап 2: CLI |

Отчёты с топ-3 и rerank лежат в **`data/results/`** (см. [../README.md](../README.md)), не дублируются здесь.

Пересборка отчётов: `python scripts/build_ranking_comparison_report.py`, `python scripts/build_rerank_comparison_report.py`.
