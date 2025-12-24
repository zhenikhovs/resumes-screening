import json
from pathlib import Path
import numpy as np

# Папка с результатами TF-IDF
results_folder = Path("../../data/results/tfidf_results-1/")  # <- укажи свою папку

summary = {}

for file in results_folder.glob("tfidf_*.json"):
    query = file.stem.replace("tfidf_", "")
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Для каждой вакансии берем score самого релевантного резюме
    top_scores = [vac["candidates"][0]["score"] if vac["candidates"] else 0.0 for vac in data]

    summary[query] = {
        "vacancies": len(data),
        "average_top_score": np.mean(top_scores),
        "median_top_score": np.median(top_scores),
        "min_top_score": np.min(top_scores),
        "max_top_score": np.max(top_scores)
    }

# Печать статистики
for query, stats in summary.items():
    print(f"Query: {query}")
    print(f"  Вакансий: {stats['vacancies']}")
    print(f"  Средний top-score: {stats['average_top_score']:.4f}")
    print(f"  Медианный top-score: {stats['median_top_score']:.4f}")
    print(f"  Минимальный top-score: {stats['min_top_score']:.4f}")
    print(f"  Максимальный top-score: {stats['max_top_score']:.4f}\n")
