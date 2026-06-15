# Материал для главы: этап 1 — сопоставление резюме и вакансии (ранжирование)

Документ для написания текста диссертации. Соответствует коду в `services/ranking/`, `services/preprocessing/`, `config/pipeline_config.py`.

**Общая картина системы:** [DISSERTATION_SYSTEM_OVERVIEW.md](DISSERTATION_SYSTEM_OVERVIEW.md).  
**Этап 2 (интервью):** [DISSERTATION_INTERVIEW.md](DISSERTATION_INTERVIEW.md).

Связанные файлы: [PIPELINE_RANKING.md](PIPELINE_RANKING.md), [PIPELINE_COMMANDS.md](PIPELINE_COMMANDS.md), [first_step/](first_step/README.md), отчёты в `data/results/`.

---

## 1. Постановка задачи

**Цель этапа:** для каждой вакансии оценить степень соответствия резюме кандидатов и сформировать **ранжированный список** с отбором наиболее релевантных (top-K или по порогу).

**Формально:** задача **Learning-to-Rank (LTR)** на уровне одной вакансии: множество кандидатов (резюме) → скалярный score → сортировка → подмножество после динамического порога.

**Вход:** подготовленные тексты вакансий и резюме (форматы classical и transformer).  
**Выход:** JSON с кандидатами, `score_norm`, порогом, `top_k_candidates`; опционально — пересортировка cross-encoder.

---

## 2. Сбор и подготовка данных

### 2.1. Источник

Данные с **hh.ru**: вакансии и резюме по поисковым запросам (например `backend developer`, `frontend developer`).

Цепочка (как в репозитории):

1. Краткие карточки → полные JSON (`hh_fetch_full`, `hh_fetch_full_vacancies`).
2. **Pre-clean** — удаление служебных полей, очистка HTML.
3. **Clean** — два представления:
   - **classical** — лемматизированные поля для BM25/TF-IDF (полный опыт в поле `experience`);
   - **transformer** — короткий `text` для би-encoder, `text_rerank` (чуть больше опыта) для cross-encoder.

Подробно: [first_step/FACT_DATA_DOWNLOAD.md](first_step/FACT_DATA_DOWNLOAD.md), [first_step/FACT_DATA_CLEANING.md](first_step/FACT_DATA_CLEANING.md).

### 2.2. Важно для transformer

- В **`text`** резюме: должность, `skill_set`, языки, позиции, **усечённые** описания последних 2 мест работы (не вся карьера).
- Поле `skills` (проза «о себе» с hh) **не** используется — только теги `skill_set`.
- При эмбеддинге к тексту дописывается суммарный стаж словами (`append_experience_to_resume_text`); для вакансии — требуемый стаж (`append_experience_to_vacancy_text`). Classical этих дописок **не** использует.

---

## 3. Алгоритм первого этапа (пайплайн)

Для **каждой вакансии** отдельно, по всем резюме выбранного корпуса (`query`).

### 3.1. Фильтр по опыту (жёсткий)

Кандидат попадает в пул similarity, только если:

\[
\text{resume\_months} \geq \lfloor 0{,}8 \times \text{vacancy\_min\_months} \rfloor
\]

(`EXPERIENCE_FACTOR = 0.8`). Остальные **исключаются** из ранжирования.

### 3.2. Признак experience_match (в формуле score)

Среди прошедших в пул:

| Значение | Условие |
|----------|---------|
| **1** | `resume_months ≥ vacancy_min_months` (полный минимум вакансии) |
| **0** | в пуле только за счёт 0,8×min, полный минимум не набран |

Если у вакансии `min_experience_months = 0`, у всех в пуле `experience_match = 1`.

### 3.3. Similarity (релевантность текстов)

| Метод | Данные | Как считается |
|-------|--------|----------------|
| **BM25** | classical | Okapi BM25 по токенам (title, positions, skills, experience) |
| **TF-IDF** | classical | Косинус TF-IDF-векторов |
| **E5, MiniLM, ruSBERT, MPNet** | transformer | Косинус эмбеддингов поля `text` (+ префиксы `query:`/`passage:` для E5) |

### 3.4. Итоговый score

\[
\text{final\_score} = 0{,}9 \times \text{similarity} + 0{,}1 \times \text{experience\_match}
\]

Затем **min–max** по всем кандидатам вакансии → `score_norm` ∈ [0, 1].

### 3.5. Динамический порог и top-K

- `threshold` = **90-й перцентиль** `score_norm` по вакансии (`PERCENTILE_THRESHOLD = 90`).
- В **top_k_candidates** — до **10** кандидатов с `score_norm ≥ threshold` (`TOP_K = 10`).

---

## 4. Второй подэтап: cross-encoder rerank

**Не отдельный «этап системы»**, а уточнение порядка внутри пула после первого этапа.

1. Берутся кандидаты с `score_norm ≥ threshold` из результатов transformer-pipeline (или classical).
2. Пары (текст вакансии, текст резюме): для CE резюме — **`text_rerank`**, вакансия — `text` + стаж словами.
3. Модели: `russian` (DiTy/cross-encoder-russian-msmarco), `minilm`, `multilingual`.
4. Добавляется `rerank_score`, кандидаты пересортировываются по убыванию.

Подробно: [first_step/FACT_SECOND_STAGE_CROSS_ENCODER.md](first_step/FACT_SECOND_STAGE_CROSS_ENCODER.md).

---

## 5. Модели (для текста)

| Назначение | Модель |
|------------|--------|
| BM25 / TF-IDF | без нейросети |
| E5 | `intfloat/multilingual-e5-large` |
| MiniLM | `sentence-transformers/all-MiniLM-L6-v2` |
| ruSBERT | `ai-forever/sbert_large_nlu_ru` |
| MPNet | `all-mpnet-base-v2` |
| Cross-encoder (рус.) | `DiTy/cross-encoder-russian-msmarco` |

Полный список: [first_step/FACT_MODELS.md](first_step/FACT_MODELS.md).

---

## 6. Результаты эксперимента

### 6.1. Где лежат артефакты

| Что | Путь |
|-----|------|
| Classical (BM25) | `data/results/pipeline_classical/pipeline_classical_{query}.json` |
| Classical (TF-IDF) | `data/results/pipeline_classical/pipeline_tfidf_{query}.json` |
| Transformer | `data/results/pipeline_transformer/{method}/pipeline_{method}_{query}.json` |
| Cross-encoder | `data/results/pipeline_cross_encoder/{method}/` |
| Статистика | `data/results/pipeline_stats/` |

### 6.2. Сравнительные отчёты (для таблиц в диссертации)

- **`data/results/RANKING_COMPARISON_BY_VACANCY.md`** — топ-3 кандидата по каждому методу на одних вакансиях (backend, frontend, fullstack).
- **`data/results/RERANK_COMPARISON_BY_VACANCY.md`** — порядок до/после cross-encoder.
- **`data/results/rerank_top1_shift_stats.json`** — как часто меняется первое место после rerank.

Пересборка:

```bash
python scripts/build_ranking_comparison_report.py
python scripts/build_rerank_comparison_report.py
```

### 6.3. Качественные выводы (формулировки для главы)

См. [first_step/FACT_QUALITATIVE_SUMMARY.md](first_step/FACT_QUALITATIVE_SUMMARY.md). Кратко:

- На **узких IT-ролях** (Node.js backend, C# .NET) различие между **лексикой (BM25/TF-IDF)** и **семантикой (E5, MPNet)** выражено сильнее, чем на «широком» frontend.
- **E5** в ряде кейсов лучше согласует топ с должностью и стеком из вакансии.
- **BM25** может поднимать в топ пересечение по ключевым словам без совпадения роли.
- **MiniLM / ru_sbert** на отдельных вакансиях давали нерелевантные роли в топ-3.
- **Cross-encoder** уточняет порядок внутри уже отфильтрованного пула; влияние зависит от вакансии (см. отчёт rerank).

### 6.4. Цифры по фильтру опыта

См. [first_step/FACT_MAIN_NUMBERS.md](first_step/FACT_MAIN_NUMBERS.md) — доля резюме, прошедших фильтр 0,8×min, сжатие после порога и top-K.

---

## 7. Метрики (если нужен формальный LTR-раздел)

См. [RANKING_METRICS_AND_BETTER.md](RANKING_METRICS_AND_BETTER.md) — NDCG, MAP, MRR.  
Псевдо-разметка из топ-k: [LABELING_TOP_K.md](LABELING_TOP_K.md).

---

## 8. Веб-приложение (тот же этап 1 в UI)

В веб-интерфейсе HR запускает ту же логику: вакансия с hh + поиск резюме → pre-clean/clean → E5 + cross-encoder → топ-5.  
См. [WEB_APP.md](WEB_APP.md), [DISSERTATION_INTERVIEW.md](DISSERTATION_INTERVIEW.md) (связь с этапом 2).

---

## 9. Что писать в главе (чеклист)

1. Постановка LTR и цель отбора кандидатов по резюме.  
2. Источник данных hh.ru и двухформатная подготовка (classical / transformer).  
3. Двухуровневый учёт опыта: фильтр 0,8×min и `experience_match` в score.  
4. Описание методов similarity и формулы `final_score`.  
5. Порог 90-го перцентиля и top-10.  
6. Cross-encoder как rerank (опционально в той же главе или подпункт).  
7. Таблица/примеры из `RANKING_COMPARISON_BY_VACANCY.md` + качественные выводы.  
8. Ссылка на конфигурацию и воспроизводимость (`pipeline_config.py`, команды в [PIPELINE_COMMANDS.md](PIPELINE_COMMANDS.md)).
