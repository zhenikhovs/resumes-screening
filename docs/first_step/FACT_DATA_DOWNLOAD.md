# Факт: как скачивались данные (HeadHunter API)

Описание соответствует коду в `services/api/`, `main.py`, `vacancies.py`, `config/paths.py`. Данные берутся **только с официального API hh.ru** (`https://api.hh.ru/`), не со страниц в браузере.

---

## 1. Авторизация

**Файл:** `services/api/hh_auth.py`

- В `.env` задаются **`CLIENT_ID`** и **`CLIENT_SECRET`** (приложение в личном кабинете разработчика hh).
- При первом запуске или при протухшем токене:
  1. Открывается URL `https://hh.ru/oauth/authorize?response_type=code&client_id=...`
  2. Пользователь авторизуется и вставляет **`code`** из redirect URL.
  3. Выполняется `POST https://hh.ru/oauth/token` с `grant_type=authorization_code`, `code`, `client_id`, `client_secret`.
  4. **`access_token`** сохраняется в **`data/token.json`**.
- Перед использованием токен проверяется запросом `GET https://api.hh.ru/me` с заголовком `Authorization: Bearer <token>` и `User-Agent: ai-resume-screener/1.0`.

Без валидного токена запросы к API резюме/вакансий не выполняются.

---

## 2. Резюме

### 2.1. Краткие карточки (поиск)

**Вариант A — массовая выборка по тексту запроса** (`services/api/hh_fetch_raw.py`, вспомогательный сценарий):

- Цикл по страницам:  
  `GET https://api.hh.ru/resumes?text=<query>&page=<n>&per_page=20`
- Заголовки: `Authorization: Bearer`, `User-Agent`.
- Между страницами пауза **0.5 с** (снижение риска 429).
- Результаты объединяются в один пул (дедупликация по `id`), к каждой записи добавляется поле **`query`**.
- Сохранение: например `data/raw/resumes_raw.json` (в коде — `RAW_DIR / "resumes_raw.json"`).

**Вариант B — по одному запросу (основной путь для проекта):**

- Краткие резюме по запросу лежат в **`data/raw/part/resumes/resumes_<query>.json`**, где `<query>` = строка запроса с пробелами, заменёнными на подчёркивания (например `backend_developer`).
- Список запросов в **`main.py`**:  
  `web developer`, `frontend developer`, `php developer`, `IT project manager`, `javascript developer`, `backend developer`, `fullstack developer`, `project manager`.

### 2.2. Полные резюме

**Файл:** `services/api/hh_fetch_full.py`  
**Точка входа:** `main.py` — выбирается один `query_name` из списка, читается файл `resumes_<suffix>.json` с краткими объектами.

Для каждого элемента списка (есть поле `id`):

- Если `id` уже есть в агрегате **`data/raw/full/resumes/resumes_full.json`** — резюме не запрашивается повторно, но обновляется/дублируется в выборку по текущему `query`.
- Иначе:  
  **`GET https://api.hh.ru/resumes/{id}`**  
  с теми же заголовками, таймаут 10 с.

Обработка кодов ответа:

- **200** — тело JSON = полное резюме; добавляется **`query`** (строка запроса); дописывается в:
  - `resumes_full.json` (общий пул),
  - `data/raw/full/resumes/resumes_<query_suffix>.json` (только этот запрос).
- **404** — резюме удалено; запись убирается из файла кратких для этого query.
- **429** — остановка скрипта («лимит API»).

Итоговые **полные** резюме для дальнейшей pre-clean лежат в **`data/raw/full/resumes/`**.

---

## 3. Вакансии

### 3.1. Краткий поиск

**Файл:** `services/api/hh_fetch_vacancies.py`

- Для каждого текстового запроса из списка:
  - цикл по страницам:  
    **`GET https://api.hh.ru/vacancies?text=<query>&page=<p>&per_page=20`**
  - до `per_query` записей (по умолчанию до 100 на запрос — 5 страниц по 20).
  - Пауза **0.5 с** между страницами.
  - Каждой записи добавляется **`query`**.
- Сохранение: **`data/raw/vacancies/vacancies_<query_with_underscores>.json`**.

### 3.2. Полные вакансии

**Файл:** `services/api/hh_fetch_full_vacancies.py`  
**Точка входа:** `vacancies.py` — читается **`data/raw/part/vacancies/vacancies_<suffix>.json`** (краткие объекты с `id`).

Для каждого `id`, которого ещё нет в файле полных вакансий по этому query:

- **`GET https://api.hh.ru/vacancies/{id}`**
- **200** — полный JSON вакансии + поле **`query`** → дописывается в  
  **`data/raw/full/vacancies/vacancies_<query_suffix>.json`**.
- **404** — вакансия снята; id удаляется из краткого файла.
- **429** — остановка.

---

## 4. Цепочка в проекте (кратко)

1. Получить токен (`hh_auth`).
2. Собрать **краткие** резюме/вакансии (поиск по API или готовые `part`-файлы).
3. Пройти по id и скачать **полные** объекты (`hh_fetch_full`, `hh_fetch_full_vacancies`).
4. Далее в пайплайне: **pre_clean** и **clean** (см. `FACT_DATA_CLEANING.md`).

---

## 5. Ограничения API

- Лимиты запросов (ответ **429**) — скрипты при 429 завершают работу; часть данных может быть не докачана до повторного запуска.
- Доступ к полным резюме через API возможен только в рамках прав приложения и правил hh для работодателя/приложения.
