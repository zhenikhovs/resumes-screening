"""
Конфигурация нового pipeline ранжирования.

- Фильтр в пул: resume_experience >= 0.8 * vacancy_min_experience_months.
- experience_match = 1, если resume_experience >= vacancy_min (без 0.8), иначе 0.
- Итоговый score: 0.9 * similarity_score + 0.1 * experience_match.
"""
EXPERIENCE_FACTOR = 0.8
SIMILARITY_WEIGHT = 0.9
EXPERIENCE_MATCH_WEIGHT = 0.1
PERCENTILE_THRESHOLD = 90
TOP_K = 10

# Лимиты текста для transformer (clean_resumes): bi-encoder — короче, cross-encoder — чуть длиннее
EMBEDDING_EXPERIENCE_JOBS = 2
EMBEDDING_EXPERIENCE_MAX_CHARS = 800
RERANK_EXPERIENCE_JOBS = 3
RERANK_EXPERIENCE_MAX_CHARS = 1200
