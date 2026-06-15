"""
Метрики ранжирования: NDCG@k, MAP, MRR.

Вход: предсказанный порядок (ranked list of document ids) и список релевантностей
в том же порядке либо словарь doc_id -> relevance.
"""
import math
from typing import List, Union


def dcg_at_k(relevances: List[float], k: int) -> float:
    """DCG@k. relevances — список релевантностей в порядке предсказанного ранжирования."""
    relevances = relevances[:k]
    if not relevances:
        return 0.0
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(relevances))


def ndcg_at_k(predicted_order: List[str], relevance_by_id: dict, k: int) -> float:
    """
    NDCG@k: нормализованный DCG.
    predicted_order — порядок кандидатов (resume_id) от модели.
    relevance_by_id — словарь resume_id -> relevance (0/1 или 0,1,2).
    """
    relevances = [relevance_by_id.get(rid, 0) for rid in predicted_order]
    dcg = dcg_at_k(relevances, k)
    ideal_relevances = sorted(relevance_by_id.values(), reverse=True)[:k]
    idcg = dcg_at_k(ideal_relevances, k)
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def average_precision(predicted_order: List[str], relevance_by_id: dict) -> float:
    """Average Precision (AP) для одной вакансии (один запрос)."""
    relevances = [relevance_by_id.get(rid, 0) for rid in predicted_order]
    num_relevant = sum(1 for r in relevances if r > 0)
    if num_relevant == 0:
        return 0.0
    precisions = []
    relevant_so_far = 0
    for i, r in enumerate(relevances):
        if r > 0:
            relevant_so_far += 1
            precisions.append(relevant_so_far / (i + 1))
    return sum(precisions) / num_relevant if precisions else 0.0


def map_at_k(predicted_orders_by_vacancy: List[List[str]], relevance_by_vacancy: List[dict]) -> float:
    """MAP: среднее AP по всем вакансиям (запросам)."""
    if not predicted_orders_by_vacancy or len(predicted_orders_by_vacancy) != len(relevance_by_vacancy):
        return 0.0
    aps = [
        average_precision(order, rel_dict)
        for order, rel_dict in zip(predicted_orders_by_vacancy, relevance_by_vacancy)
    ]
    return sum(aps) / len(aps) if aps else 0.0


def reciprocal_rank(predicted_order: List[str], relevance_by_id: dict) -> float:
    """RR: 1/rank первого релевантного. Для одной вакансии."""
    for i, rid in enumerate(predicted_order):
        if relevance_by_id.get(rid, 0) > 0:
            return 1.0 / (i + 1)
    return 0.0


def mrr(predicted_orders_by_vacancy: List[List[str]], relevance_by_vacancy: List[dict]) -> float:
    """MRR: среднее RR по всем вакансиям."""
    if not predicted_orders_by_vacancy or len(predicted_orders_by_vacancy) != len(relevance_by_vacancy):
        return 0.0
    rrs = [
        reciprocal_rank(order, rel_dict)
        for order, rel_dict in zip(predicted_orders_by_vacancy, relevance_by_vacancy)
    ]
    return sum(rrs) / len(rrs) if rrs else 0.0


def ndcg_at_k_multi(
    predicted_orders_by_vacancy: List[List[str]],
    relevance_by_vacancy: List[dict],
    k: int,
) -> float:
    """Средний NDCG@k по всем вакансиям."""
    if not predicted_orders_by_vacancy or len(predicted_orders_by_vacancy) != len(relevance_by_vacancy):
        return 0.0
    ndcgs = [
        ndcg_at_k(order, rel_dict, k)
        for order, rel_dict in zip(predicted_orders_by_vacancy, relevance_by_vacancy)
    ]
    return sum(ndcgs) / len(ndcgs) if ndcgs else 0.0
