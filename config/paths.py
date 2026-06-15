"""
Единые пути проекта. Все пути относительно корня репозитория.
Запуск скриптов — из корня: python main.py или python -m services.ranking.bm25
"""
from pathlib import Path

# Корень проекта (директория, в которой лежат config/, services/, data/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PREPARED_DIR = DATA_DIR / "prepared"
RESULTS_DIR = DATA_DIR / "results"

# Сырые данные
RAW_PART_RESUMES = RAW_DIR / "part" / "resumes"
RAW_PART_VACANCIES = RAW_DIR / "part" / "vacancies"
RAW_FULL_RESUMES = RAW_DIR / "full" / "resumes"
RAW_FULL_VACANCIES = RAW_DIR / "full" / "vacancies"
RAW_RESUMES = RAW_DIR / "resumes"
RAW_VACANCIES = RAW_DIR / "vacancies"

# Подготовленные данные (после clean)
PREPARED_RESUMES = PREPARED_DIR / "resumes"
PREPARED_VACANCIES = PREPARED_DIR / "vacancies"
RESUMES_CLASSICAL = PREPARED_RESUMES / "cleaned" / "classical"
RESUMES_TRANSFORMER = PREPARED_RESUMES / "cleaned" / "transformer"
VACANCIES_CLASSICAL = PREPARED_VACANCIES / "cleaned" / "classical"
VACANCIES_TRANSFORMER = PREPARED_VACANCIES / "cleaned" / "transformer"
PRE_CLEANED_RESUMES = PREPARED_RESUMES / "pre-cleaned"
PRE_CLEANED_VACANCIES = PREPARED_VACANCIES / "pre-cleaned"

# Результаты ранжирования
BM25_RESULTS = RESULTS_DIR / "bm25_results"
TFIDF_RESULTS = RESULTS_DIR / "tfidf_results"
E5_RESULTS = RESULTS_DIR / "e5_results"
MINILM_RESULTS = RESULTS_DIR / "minilm_results"
RUSBERT_RESULTS = RESULTS_DIR / "rusbert_results"
MPNET_RESULTS = RESULTS_DIR / "mpnet_results"

# Токен и логи
TOKEN_FILE = DATA_DIR / "token.json"

# Разметка (псевдо-labels по топ-k из результатов ранжирования)
LABELS_DIR = DATA_DIR / "labels"

# Новый pipeline ранжирования (фильтр по опыту + similarity + threshold + top-k)
PIPELINE_CLASSICAL_RESULTS = RESULTS_DIR / "pipeline_classical"
PIPELINE_TRANSFORMER_RESULTS = RESULTS_DIR / "pipeline_transformer"
PIPELINE_STATS_DIR = RESULTS_DIR / "pipeline_stats"

# Второй этап ранжирования (cross-encoder reranking поверх transformer-pipeline)
PIPELINE_CROSS_ENCODER_RESULTS = RESULTS_DIR / "pipeline_cross_encoder"

# Видео-интервью (этап 2 диссертации: оценка ответов)
INTERVIEWS_DIR = DATA_DIR / "interviews"
INTERVIEWS_SCENARIOS_DIR = INTERVIEWS_DIR / "scenarios"
INTERVIEWS_RESULTS_DIR = RESULTS_DIR / "interviews"
