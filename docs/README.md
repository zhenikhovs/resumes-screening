# Документация проекта

Материалы для **диссертации** и для **запуска** системы.

---

## Для написания диссертации (главное)

| Файл | Содержание |
|------|------------|
| **[DISSERTATION_SYSTEM_OVERVIEW.md](DISSERTATION_SYSTEM_OVERVIEW.md)** | **Общее описание всей системы:** цель, архитектура, оба этапа, веб, технологии, введение |
| **[DISSERTATION_RANKING.md](DISSERTATION_RANKING.md)** | **Этап 1:** LTR, данные, алгоритм, модели, эксперимент, выводы |
| **[DISSERTATION_INTERVIEW.md](DISSERTATION_INTERVIEW.md)** | **Этап 2:** видео-интервью, запись, ASR, Groq, одобрение |

**Порядок чтения:** сначала `DISSERTATION_SYSTEM_OVERVIEW.md`, затем два файла по этапам.

---

## Запуск и веб

| Файл | Зачем |
|------|--------|
| [WEB_APP.md](WEB_APP.md) | Vue 3 + FastAPI: HR, кандидат, скриншоты |
| [PIPELINE_COMMANDS.md](PIPELINE_COMMANDS.md) | Команды `run.py`: clean, ranking, rerank, interview |
| [PIPELINE_RANKING.md](PIPELINE_RANKING.md) | Кратко: алгоритм ранжирования |
| [INTERVIEW_PIPELINE.md](INTERVIEW_PIPELINE.md) | Кратко: CLI интервью |
| [INTERVIEW_DETAILED.md](INTERVIEW_DETAILED.md) | **Подробно:** как работает интервью (веб, API, запись, обработка, файлы) |

Корень репозитория: `pip install -r requirements.txt`, `AGENTS.md`, `PROJECT_STRUCTURE.md`.

---

## Факты по этапу 1 (детали для сносок)

Папка [first_step/](first_step/README.md): скачивание hh, clean, модели, cross-encoder, цифры, качественные выводы.

| Отчёт (таблицы) | Путь |
|-----------------|------|
| Сравнение методов (топ-3) | `data/results/RANKING_COMPARISON_BY_VACANCY.md` |
| До/после rerank | `data/results/RERANK_COMPARISON_BY_VACANCY.md` |

```bash
python scripts/build_ranking_comparison_report.py
python scripts/build_rerank_comparison_report.py
```

---

## Метрики LTR (по желанию)

| Файл | Зачем |
|------|--------|
| [RANKING_METRICS_AND_BETTER.md](RANKING_METRICS_AND_BETTER.md) | NDCG, MAP, MRR |
| [LABELING_TOP_K.md](LABELING_TOP_K.md) | Псевдо-разметка из top-k |
