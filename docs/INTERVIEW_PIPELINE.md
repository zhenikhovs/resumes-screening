# Этап 2: видео-интервью (реализовано)

Оценка ответов кандидата: видео → аудио → Whisper → Groq (LLM) → балл по вопросу → среднее и решение **одобрен / не одобрен** (порог **≥ 7**).

Текст для главы: [DISSERTATION_INTERVIEW.md](DISSERTATION_INTERVIEW.md).  
Полное описание: [INTERVIEW_DETAILED.md](INTERVIEW_DETAILED.md).

---

## Зависимости

- **ffmpeg** в PATH
- Python: `pip install -r requirements.txt` (whisper, langchain-groq, python-dotenv)
- **`GROQ_API_KEY`** в `.env` или окружении

---

## Структура данных

```
data/interviews/scenarios/{query}.json     # вопросы + эталоны
data/interviews/{interview_id}/
  meta.json
  interview_summary.json                   # после finalize
  questions/{question_id}/
    raw.mp4
    audio_16k.wav
    transcript.json
    evaluation.json
data/results/interviews/{interview_id}_{query}.json
```

---

## Сценарий (JSON)

Файл `data/interviews/scenarios/backend_developer.json`:

- `query` — связь с вакансией (`vacancies_{query}.json` в transformer)
- `pass_threshold` — по умолчанию 7
- `questions[]`: `question_id`, `question`, `reference_answer`
- опционально `vacancy_text` — если не задан, текст вакансии подставляется из cleaned transformer

---

## Команды

```bash
# 1. Создать интервью (метаданные)
python run.py interview init \
  --interview-id int_001 \
  --candidate-id cand_42 \
  --query backend_developer

# 2. Обработать один ответ (одно видео = один вопрос)
python run.py interview process \
  --interview-id int_001 \
  --question-id q_rest_api \
  --video path/to/answer_q1.mp4

# Повторить для q_db_index, q_scaling ...

# 3. Итог: средний балл и approved
python run.py interview finalize --interview-id int_001
```

Флаги `process`: `--skip-extract`, `--skip-transcribe`, `--skip-evaluate` — для повторного прогона отдельных шагов.

---

## Правило одобрения

\[
\text{interview\_score\_avg} = \mathrm{mean}(\text{score по каждому вопросу})
\]

\[
\text{approved} = (\text{interview\_score\_avg} \geq 7)
\]

---

## Промпт

См. `services/interview/prompts.py` — оценка по смыслу, учёт ASR, JSON `{ "score", "summary" }`.
