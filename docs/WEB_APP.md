# Веб-приложение (полный сценарий для скриншотов)

## Что делает система

1. HR вставляет **ссылку на вакансию hh.ru** → загрузка и **pre-clean + clean** (как в `run.py`).
2. HR вводит **поисковую строку** → поиск и скачивание резюме с hh (или **demo**-корпус, если нет `data/token.json`).
3. **Ранжирование E5 + cross-encoder** по **50** резюме → **топ-5** в интерфейсе (`CAMPAIGN_MAX_FULL_RESUMES`, `RANKING_TOP_N` в `.env`).
4. HR загружает **JSON с вопросами и эталонами** (или использует шаблон).
5. HR отправляет **приглашения** (SMTP или лог в `data/campaigns/{id}/invitation_emails.log`).
6. Кандидат проходит **видео-интервью** по вопросам.
7. **Whisper + Groq** → оценки и **одобрение при среднем ≥ 7**.

## Подготовка

```bash
pip install -r requirements.txt
# .env
GROQ_API_KEY=...
WEB_HR_EMAIL=hr@company.com
WEB_HR_PASSWORD=...
SECRET_KEY=long-random-string

# Для реального поиска резюме на hh (не demo):
# CLIENT_ID=... CLIENT_SECRET=...
# HH_CONTACT_EMAIL=your@email.com   # в User-Agent для api.hh.ru (можно = WEB_HR_EMAIL)
# → один раз: python -c "from services.api.hh_auth import get_access_token; get_access_token()"

# Сколько резюме на кампанию (по умолчанию 50 в корпус, 5 в UI):
# CAMPAIGN_RESUME_SEARCH_PAGES=3
# CAMPAIGN_MAX_FULL_RESUMES=50
# RANKING_TOP_N=5

# Опционально SMTP:
# SMTP_HOST=smtp.gmail.com
# SMTP_USER=...
# SMTP_PASSWORD=...
# APP_PUBLIC_URL=http://localhost:5173
```

**Рекомендуется** удалить старую БД после обновления: `rm data/app.db`

```bash
uvicorn web_api.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

## Скриншоты — порядок экранов

| # | Роль | Экран |
|---|------|--------|
| 1 | HR | Логин |
| 2 | HR | Новая кампания: URL + **поисковая строка** |
| 3 | HR | Кампания: шаги «Данные → Clean → Ранжирование → Готово» |
| 4 | HR | Вкладка **Кандидаты** — топ-5 |
| 5 | HR | Вкладка **Сценарий** — загрузка JSON |
| 6 | HR | Приглашения + пароли / SMTP |
| 7 | Кандидат | Собеседование: вопрос, камера, запись |
| 8 | HR | Вкладка **Результаты** — баллы и одобрение |

## Формат JSON сценария

См. `data/interviews/scenarios/backend_developer.json` или загрузите свой:

```json
{
  "pass_threshold": 7,
  "questions": [
    {
      "question_id": "q1",
      "question": "Текст вопроса",
      "reference_answer": "Эталонный ответ"
    }
  ]
}
```

## Токен HeadHunter (`data/token.json`)

| Ситуация | Поведение |
|----------|-----------|
| Файла **нет** | **Demo**: резюме из готового корпуса (`backend_developer`), бейдж demo в UI |
| Файл **есть**, токен **просрочен/невалиден** | Кампания **падает с ошибкой** — нужна переавторизация, demo **не** включается |
| Токен **действует** | Поиск резюме на hh.ru по вашей строке |

Переавторизация (интерактивно, в терминале):

```bash
# в .env: CLIENT_ID, CLIENT_SECRET
python -c "from services.api.hh_auth import get_access_token; get_access_token()"
```

Откроется браузер hh.ru → после входа вставьте `code` из URL → новый токен перезапишет `data/token.json`.
