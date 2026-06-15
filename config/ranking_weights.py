"""
Веса полей для ранжирования BM25 и TF-IDF (classical).

Обоснование:
- skills (3.0): главный сигнал для IT-подбора — совпадение навыков вакансии и резюме.
- title (2.0): должность/позиция сильно коррелирует с релевантностью.
- experience (1.0): текст опыта и требований — вспомогательный сигнал (часто длинный, шумный).
- experience_months (1.0): бинарное попадание в диапазон опыта вакансии — важный фильтр.

Сумма весов = 7.0; итоговый score = взвешенная сумма нормализованных по полю скоров / 7,
затем per-vacancy min-max → [0, 1] для сопоставимости методов и метрик.

Подбор весов по NDCG@k на валидации (grid/opt) даст обоснование по данным;
см. docs/RANKING_METRICS_AND_BETTER.md.
"""
# Общие веса для BM25 и TF-IDF (поля должны совпадать по смыслу)
CLASSICAL_WEIGHTS = {
    "title": 2.0,
    "skills": 3.0,
    "experience": 1.0,           # BM25: experience; TF-IDF: experience_text
    "experience_months": 1.0,
}

# Алиас для TF-IDF (там поле называется experience_text)
TFIDF_WEIGHTS = {
    "title": CLASSICAL_WEIGHTS["title"],
    "skills": CLASSICAL_WEIGHTS["skills"],
    "experience_text": CLASSICAL_WEIGHTS["experience"],
    "experience_months": CLASSICAL_WEIGHTS["experience_months"],
}
