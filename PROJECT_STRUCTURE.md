# Структура проекта

Запуск всех скриптов — **из корня репозитория**: `python main.py`, `python -m services.ranking.bm25` и т.д.

## Директории

```
config/                 # Конфигурация
  paths.py              # Единые пути (data/, raw, prepared, results)

services/
  utils.py              # load_json, save_json, safe_get, setup_logger

  api/                  # Работа с HH.ru
    hh_auth.py          # Токен OAuth
    hh_fetch_raw.py     # Краткие резюме по query
    hh_fetch_full.py    # Полные резюме по ID
    hh_fetch_vacancies.py
    hh_fetch_full_vacancies.py

  preprocessing/       # Предобработка текстов и данных
    clean_text.py       # Очистка требований вакансии (NOISE_PATTERNS)
    normalization/
      tech_aliases.py   # Нормализация тех. терминов
    pre_clean_resumes.py   # Сырые резюме → pre-cleaned
    pre_clean_vacancies.py # Сырые вакансии → pre-cleaned
    clean_resumes.py       # pre-cleaned резюме → classical + transformer
    clean_vacancies.py     # pre-cleaned вакансии → classical + transformer

  ranking/              # Ранжирование (Resume–Vacancy Matching)
    score_utils.py      # tokenize, normalize_scores (min-max)
    experience_text.py  # Опыт в текст для эмбеддингов
    bm25.py             # BM25 по полям
    tfidf.py            # TF-IDF по полям
    e5.py               # Эмбеддинги E5
    minilm.py
    ru_sbert.py
    mpnet.py

  evaluation/           # Разметка по топ-k, метрики NDCG/MAP/MRR
    build_labels_from_ranking.py  # Разметка: топ-k из результатов → data/labels/
    metrics.py                    # NDCG@k, MAP, MRR
    evaluate_ranking.py           # Оценка метода по файлу разметки
    countrow.py

  training/             # Обучение LTR (заглушка)
    README.md
```

## Score и нормализация

- **Min-max считается по конкретной вакансии**, не по всем файлам: для каждой вакансии берётся пул её кандидатов (резюме из одного query-файла), по ним считаются min и max, и скоры приводятся к [0, 1]. Лучший кандидат по этой вакансии → 1.0, худший → 0.0. Так корректно для ранжирования и для NDCG/MAP.
- **Итоговый score не превышает 1** и сопоставим между методами (BM25, TF-IDF, E5 и т.д.).
- **«BM25 ранжирует лучше»** имеет смысл сравнивать по метрикам ранжирования (NDCG@k, MAP, MRR), а не по величине score: порядок кандидатов даёт ранжирование, метрики измеряют его качество.

Точки входа ранжирования: `python -m services.ranking.bm25`, `services.ranking.tfidf`, `e5`, `minilm`, `ru_sbert`, `mpnet`.

## Данные (config.paths)

- Сырые: `data/raw/part/resumes`, `data/raw/part/vacancies`, `data/raw/full/...`, `data/raw/resumes`, `data/raw/vacancies`.
- Подготовленные: `data/prepared/resumes/cleaned/classical`, `.../transformer`, то же для vacancies.
- Результаты: `data/results/bm25_results`, `tfidf_results`, `e5_results` и т.д.
