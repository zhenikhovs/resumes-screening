"""
Разметка по топ-k: без ручной разметки и логов.

Берём результаты ранжирования одного метода (например BM25). Для каждой вакансии
топ-k кандидатов помечаем как релевантные (relevance=1), остальных — 0.
Обоснование: порог отсечки — «столько кандидатов мы считаем релевантными для оценки».
"""
import argparse
from pathlib import Path

from config.paths import RESULTS_DIR, LABELS_DIR
from config.labels_config import LABELS_TOP_K, LABELS_SOURCE_METHOD
from services.utils import load_json, save_json


def build_labels(
    results_dir: Path,
    top_k: int,
    output_path: Path,
) -> list:
    """
    Читает все *_<query>.json из results_dir, для каждой вакансии помечает
    топ-k кандидатов как relevance=1, остальных 0. Возвращает список пар с relevance.
    """
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    # Файлы вида bm25_backend_developer.json, tfidf_*.json и т.д.
    for path in sorted(results_dir.glob("*.json")):
        data = load_json(path)
        if not isinstance(data, list):
            continue
        for vacancy in data:
            vacancy_id = vacancy.get("vacancy_id")
            candidates = vacancy.get("candidates") or []
            for i, c in enumerate(candidates):
                resume_id = c.get("resume_id")
                if resume_id is None:
                    continue
                relevance = 1 if i < top_k else 0
                rows.append({
                    "vacancy_id": str(vacancy_id),
                    "resume_id": str(resume_id),
                    "relevance": relevance,
                })
    save_json(output_path, rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Разметка по топ-k из результатов ранжирования")
    parser.add_argument("--method", default=LABELS_SOURCE_METHOD, help="Метод для имени папки (bm25, tfidf, e5, ...)")
    parser.add_argument("--results-dir", default=None, help="Путь к папке с JSON результатов (по умолчанию data/results/<method>_results)")
    parser.add_argument("--top-k", type=int, default=LABELS_TOP_K, help="Сколько кандидатов считать релевантными")
    parser.add_argument("--output", default=None, help="Выходной JSON (по умолчанию data/labels/top_k_<method>_k<k>.json)")
    args = parser.parse_args()

    results_dir = Path(args.results_dir) if args.results_dir else RESULTS_DIR / f"{args.method}_results"
    if not results_dir.exists():
        print(f"❌ Папка не найдена: {results_dir}")
        print("Сначала запустите ранжирование, например: python -m services.ranking.bm25")
        return

    output_path = Path(args.output) if args.output else LABELS_DIR / f"top_k_{args.method}_k{args.top_k}.json"
    rows = build_labels(results_dir, args.top_k, output_path)
    n_relevant = sum(1 for r in rows if r["relevance"] == 1)
    print(f"✅ Разметка сохранена: {output_path}")
    print(f"   Всего пар: {len(rows)}, релевантных (1): {n_relevant}")


if __name__ == "__main__":
    main()
