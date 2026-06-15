"""Настройки пайплайна видео-интервью (этап 2)."""

# Порог прохождения: средний балл по всем вопросам интервью
INTERVIEW_PASS_THRESHOLD = 7.0

# Groq LLM (как в ноутбуке ТГ_AI_рекрутер)
LLM_MODEL_NAME = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.1

# ASR: whisper | faster-whisper (faster-whisper — опционально, если установлен)
ASR_ENGINE = "whisper"
WHISPER_MODEL = "small"

# Аудио для ASR
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1

# Округление среднего балла в interview_summary
INTERVIEW_AVG_DECIMALS = 2
