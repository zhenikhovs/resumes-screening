# Факты и ключевые цифры (этап 1 + очистка данных)

Файл сделан как “выжимка для текста”: только главное, без деталей моделей и перебора.

## 1) Фильтрация резюме по опыту (этап 1)

В пайплайне для каждой вакансии перед similarity считается:

- `n_resumes_before_filter` — число резюме **до** фильтрации по опыту
- `n_resumes_after_filter` — число резюме **после** фильтрации по опыту

### Как считалось для каждого query

Для каждого `query` я взял файл `data/results/pipeline_classical/pipeline_classical_<query>.json`.
Дальше по каждой вакансии в этом файле прочитал `n_resumes_before_filter` и `n_resumes_after_filter`, и усреднил по всем вакансиям данного query.

Правило фильтра (как в коде):

- `vacancy_min = vacancy.min_experience_months` (если нет, то `0`)
- `T_exp = floor(0.8 * vacancy_min)` (в коде используется `int(EXPERIENCE_FACTOR * ...)` при `EXPERIENCE_FACTOR = 0.8`)
- резюме проходит, если `resume.total_experience_months >= T_exp`

### По каждому query (средние по вакансиям)

- `IT_project_manager`: `523.00 → 508.80`
- `backend_developer`: `528.00 → 400.43`
- `frontend_developer`: `362.00 → 273.94`
- `fullstack_developer`: `550.00 → 419.29`
- `javascript_developer`: `1059.00 → 819.49`
- `php_developer`: `469.00 → 412.47`
- `project_manager`: `1011.00 → 975.42`
- `web_developer`: `716.00 → 580.47`

Примечание: фильтр применяется **до** similarity, поэтому именно `n_resumes_after_filter` попадает дальше в BM25/TF-IDF/эмбеддинги.

## 2) Очистка и сжатие данных (сколько “убрало” pre-clean и clean)

### Как считалось

Я считал не байты, а число строк (`кол-во newline-строк`) в конкретных JSON-файлах:
- `data/raw/full/resumes/resumes_<query>.json` -> `data/prepared/resumes/pre-cleaned/resumes_<query>.json`
- `data/prepared/resumes/cleaned/classical/resumes_<query>.json`
- `data/prepared/resumes/cleaned/transformer/resumes_<query>.json`

Аналогично для вакансий: `vacancies_<query>.json` в тех же стадиях.

Ниже — только “по каждому запросу”, без общей суммы.

### Резюме

- записи (resumes): **5218** (кол-во объектов одинаково на всех стадиях; ниже именно строки)

| query | raw/full (строк) | pre-cleaned (строк) | cleaned (classical) (строк) | cleaned (transformer) (строк) |
|------|--------------------|----------------------|--------------------------------|----------------------------------|
| `IT_project_manager` | 244174 | 199716 | 8263 | 3140 |
| `backend_developer` | 187996 | 145903 | 6670 | 3170 |
| `frontend_developer` | 132590 | 103214 | 4686 | 2174 |
| `fullstack_developer` | 198705 | 154571 | 7124 | 3302 |
| `javascript_developer` | 374127 | 288723 | 13277 | 6356 |
| `php_developer` | 187021 | 147919 | 6498 | 2816 |
| `project_manager` | 451103 | 365446 | 15778 | 6068 |
| `web_developer` | 285321 | 223548 | 9988 | 4298 |

### Вакансии

- записи (vacancies): **795** (кол-во объектов одинаково на всех стадиях; ниже именно строки)

| query | raw/full (строк) | pre-cleaned (строк) | cleaned (classical) (строк) | cleaned (transformer) (строк) |
|------|--------------------|----------------------|--------------------------------|----------------------------------|
| `IT_project_manager` | 16337 | 5514 | 982 | 688 |
| `backend_developer` | 16944 | 5915 | 1002 | 702 |
| `frontend_developer` | 16336 | 5746 | 992 | 695 |
| `fullstack_developer` | 17352 | 6032 | 1002 | 702 |
| `javascript_developer` | 16992 | 5947 | 1002 | 702 |
| `php_developer` | 16698 | 5886 | 982 | 688 |
| `project_manager` | 17204 | 5845 | 1002 | 702 |
| `web_developer` | 16478 | 5793 | 1002 | 702 |

### Что именно “убирается” (кратко по коду)

- `pre_clean_*` удаляет служебные/чувствительные поля и чистит `description` вакансий от HTML-разметки.
- `clean_*` формирует два представления для разных этапов:
  - `classical`: более “текстовое” и нормализованное представление для BM25/TF-IDF
  - `transformer`: компактный текст-конспект для эмбеддингов (без тяжёлых структур hh API)

