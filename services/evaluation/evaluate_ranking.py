"""
Оценка результатов ранжирования по метрикам NDCG@k, MAP, MRR.

Ожидает:
- файл разметки (из build_labels_from_ranking): список {vacancy_id, resume_id, relevance};
- папку с результатами ранжирования (например data/results/tfidf_results/).

Считает метрики для выбранного метода относительно этой разметки.
"""
import argparse
from pathlib import Path
from collections import defaultdict

from config.paths import RESULTS_DIR, LABELS_DIR
from services.utils import load_json
from services.evaluation.metrics import ndcg_at_k_multi, map_at_k, mrr


def load_labels_as_dict(labels_path: Path) -> dict:
    """
    Загружает labels (список {vacancy_id, resume_id, relevance})
    и возвращает dict: vacancy_id -> {resume_id: relevance}.
    """
    rows = load_json(labels_path)
    if not isinstance(rows, list):
        return {}
    by_vacancy = defaultdict(dict)
    for r in rows:
        vid = str(r.get("vacancy_id", ""))
        rid = str(r.get("resume_id", ""))
        rel = r.get("relevance", 0)
        by_vacancy[vid][rid] = rel
    return dict(by_vacancy)


def load_results_orders(results_dir: Path) -> tuple:
    """
    Загружает все JSON из results_dir, возвращает:
    - list of predicted orders (каждый — список resume_id по убыванию score),
    - list of relevance dicts (для каждой вакансии: {resume_id: relevance}),
    - порядок вакансий должен совпадать (по vacancy_id из файлов).
    """
    predicted_orders = []
    relevance_by_vacancy = []
    labels_global = None  # будем заполнять при первом проходе или передавать снаружи

    for path in sorted(results_dir.glob("*.json")):
        data = load_json(path)
        if not isinstance(data, list):
            continue
        for vacancy in data:
            vid = str(vacancy.get("vacancy_id", ""))
            candidates = vacancy.get("candidates") or []
            order = [str(c.get("resume_id")) for c in candidates if c.get("resume_id") is not None]
            predicted_orders.append(order)
            # relevance для этой вакансии нужно взять из labels — заполним в run_evaluate
            relevance_by_vacancy.append((vid, order))

    return predicted_orders, relevance_by_vacancy


def run_evaluate(labels_path: Path, results_dir: Path, k_list: list = (5, 10)):
    """Загружает labels и results, считает метрики."""
    labels_by_vacancy = load_labels_as_dict(labels_path)
    if not labels_by_vacancy:
        print("❌ Нет разметки или пустой файл. Запустите: python -m services.evaluation.build_labels_from_ranking")
        return

    predicted_orders = []
    relevance_list = []
    for path in sorted(results_dir.glob("*.json")):
        data = load_json(path)
        if not isinstance(data, list):
            continue
        for vacancy in data:
            vid = str(vacancy.get("vacancy_id", ""))
            rel_dict = labels_by_vacancy.get(vid)
            if rel_dict is None:
                continue
            candidates = vacancy.get("candidates") or []
            order = [str(c.get("resume_id")) for c in candidates if c.get("resume_id") is not None]
            predicted_orders.append(order)
            relevance_list.append(rel_dict)

    if not predicted_orders:
        print("❌ Нет данных в результатах или нет пересечения vacancy_id с разметкой.")
        return

    print(f"Вакансий с разметкой: {len(predicted_orders)}")
    for k in k_list:
        ndcg = ndcg_at_k_multi(predicted_orders, relevance_list, k)
        print(f"  NDCG@{k}: {ndcg:.4f}")
    print(f"  MAP:    {map_at_k(predicted_orders, relevance_list):.4f}")
    print(f"  MRR:    {mrr(predicted_orders, relevance_list):.4f}")


def main():
    parser = argparse.ArgumentParser(description="Оценка ранжирования по NDCG, MAP, MRR")
    parser.add_argument("--labels", default=None, help="Путь к JSON с разметкой (по умолчанию data/labels/top_k_bm25_k5.json)")
    parser.add_argument("--method", required=True, help="Метод: bm25, tfidf, e5, minilm, ru_sbert, mpnet")
    parser.add_argument("--results-dir", default=None, help="Папка с JSON результатов (по умолчанию data/results/<method>_results)")
    parser.add_argument("--k", type=int, nargs="+", default=[5, 10], help="k для NDCG@k")
    args = parser.parse_args()

    if args.labels:
        labels_path = Path(args.labels)
    else:
        from config.labels_config import LABELS_TOP_K, LABELS_SOURCE_METHOD
        labels_path = LABELS_DIR / f"top_k_{LABELS_SOURCE_METHOD}_k{LABELS_TOP_K}.json"

    if not labels_path.exists():
        print(f"❌ Файл разметки не найден: {labels_path}")
        print("Сгенерируйте: python -m services.evaluation.build_labels_from_ranking --method bm25 --top-k 5")
        return

    results_dir = Path(args.results_dir) if args.results_dir else RESULTS_DIR / f"{args.method}_results"
    if not results_dir.exists():
        print(f"❌ Папка результатов не найдена: {results_dir}")
        return

    print(f"Разметка: {labels_path}")
    print(f"Результаты: {results_dir}")
    run_evaluate(labels_path, results_dir, args.k)


if __name__ == "__main__":
    main()
