import json
from pathlib import Path
import numpy as np

results_folder = Path("../../data/results/bm25_results/")

summary_stats = []

for result_file in results_folder.glob("bm25_*.json"):
    query = result_file.stem.replace("bm25_", "")
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    vacancy_scores = []
    for vacancy in data:
        candidates = vacancy["candidates"]
        if not candidates:
            continue
        # берем score первого кандидата (самый высокий)
        top_score = candidates[0]["score"]
        vacancy_scores.append(top_score)

    if not vacancy_scores:
        continue

    stats = {
        "query": query,
        "num_vacancies": len(data),
        "avg_top_score": float(np.mean(vacancy_scores)),
        "min_top_score": float(np.min(vacancy_scores)),
        "max_top_score": float(np.max(vacancy_scores)),
        "median_top_score": float(np.median(vacancy_scores))
    }
    summary_stats.append(stats)

# Выводим результаты
for s in summary_stats:
    print(f"Query: {s['query']}")
    print(f"  Вакансий: {s['num_vacancies']}")
    print(f"  Средний top-score: {s['avg_top_score']:.4f}")
    print(f"  Минимальный top-score: {s['min_top_score']:.4f}")
    print(f"  Максимальный top-score: {s['max_top_score']:.4f}")
    print(f"  Медианный top-score: {s['median_top_score']:.4f}\n")
