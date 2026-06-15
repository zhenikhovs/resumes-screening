"""
Второй этап ранжирования для классических моделей (BM25 / TF-IDF):
reranking с помощью cross-encoder поверх результатов classical-pipeline.

1. Берём результаты первого этапа:
   - BM25:  data/results/pipeline_classical/pipeline_classical_<query>.json
   - TF-IDF: data/results/pipeline_classical/pipeline_tfidf_<query>.json
2. Для каждой вакансии:
   - берём только тех кандидатов, у кого score_norm >= threshold (т.е. прошли dynamic threshold);
   - по resume_id находим текст резюме в data/prepared/resumes/cleaned/classical/resumes_<query>.json;
   - формируем пары (vacancy_text, resume_text) на основе classical-текстов;
   - прогоняем через cross-encoder батчами;
   - добавляем rerank_score и пересортировываем кандидатов по нему (по убыванию).
3. Сохраняем результат в:
   data/results/pipeline_cross_encoder/<method>/cross_encoder_<method>_<model_key>_<query>.json
   где method ∈ {"bm25", "tfidf"}.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm
from sentence_transformers import CrossEncoder

from config.paths import (
    RESUMES_CLASSICAL,
    VACANCIES_CLASSICAL,
    PIPELINE_CLASSICAL_RESULTS,
    PIPELINE_CROSS_ENCODER_RESULTS,
)
from services.utils import load_json, save_json
from services.ranking.pipeline_classical import resume_to_text, vacancy_to_text

from services.ranking.cross_encoder_rerank import CROSS_ENCODER_MODELS, DEFAULT_CROSS_ENCODER_MODEL, DEFAULT_BATCH_SIZE


def _load_vacancies_and_resumes_classical(query: str) -> Tuple[list, dict]:
    """Загружает вакансии и резюме для заданного query из classical-корпуса."""
    vac_path = VACANCIES_CLASSICAL / f"vacancies_{query}.json"
    res_path = RESUMES_CLASSICAL / f"resumes_{query}.json"
    vacancies = load_json(vac_path) or []
    resumes = load_json(res_path) or []
    resumes_by_id = {str(r.get("id")): r for r in resumes}
    return vacancies, resumes_by_id


def _build_pairs_for_vacancy_classical(
    vacancy_entry: dict,
    vacancies_by_id: dict,
    resumes_by_id: dict,
) -> Tuple[List[Tuple[str, str]], List[dict]]:
    """
    Для одной вакансии из classical pipeline-результатов строит пары (vacancy_text, resume_text)
    только для кандидатов с score_norm >= threshold.

    Возвращает:
      - pairs: список (vacancy_text, resume_text)
      - candidates: список словарей-кандидатов (будем в них добавлять rerank_score)
    """
    vid = str(vacancy_entry.get("vacancy_id"))
    threshold = vacancy_entry.get("threshold")
    candidates_all = vacancy_entry.get("candidates") or []

    v_src = vacancies_by_id.get(vid)
    if not v_src:
        return [], []

    vacancy_text = vacancy_to_text(v_src)

    pairs: List[Tuple[str, str]] = []
    selected_candidates: List[dict] = []

    for c in candidates_all:
        if threshold is not None and c.get("score_norm", 0.0) < threshold:
            continue
        rid = str(c.get("resume_id"))
        r_src = resumes_by_id.get(rid)
        if not r_src:
            continue
        resume_text = resume_to_text(r_src)
        pairs.append((vacancy_text, resume_text))
        selected_candidates.append(c)

    return pairs, selected_candidates


def run_cross_encoder_rerank_classical(
    method: str = "bm25",
    model_name: str | None = None,
    model_key: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    """
    Запускает второй этап ранжирования для классического метода.

    method: "bm25" или "tfidf".
    model_name: полное имя cross-encoder модели (если None, берётся из model_key или default).
    model_key: ключ из CROSS_ENCODER_MODELS (russian, minilm, multilingual); используется в имени файла.
    batch_size: размер батча для предсказаний (32 или 64).
    """
    method = (method or "bm25").strip().lower()
    if method not in {"bm25", "tfidf"}:
        print(f"❌ Неизвестный classical-метод: {method}. Ожидается bm25 или tfidf.")
        return

    if model_key and model_key in CROSS_ENCODER_MODELS:
        name = CROSS_ENCODER_MODELS[model_key]
        if model_name is None:
            model_name = name
    elif model_name is None:
        model_name = DEFAULT_CROSS_ENCODER_MODEL
        model_key = model_key or "russian"

    # Вход: pipeline_classical_*.json или pipeline_tfidf_*.json
    prefix = "pipeline_classical" if method == "bm25" else "pipeline_tfidf"
    in_dir = PIPELINE_CLASSICAL_RESULTS
    if not in_dir.exists():
        print(f"❌ Нет директории с результатами classical-pipeline: {in_dir}")
        return

    out_dir = PIPELINE_CROSS_ENCODER_RESULTS / method
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔁 Cross-encoder reranking (classical): method={method}, model={model_name}, batch_size={batch_size}")
    model = CrossEncoder(model_name)

    for path in sorted(in_dir.glob(f"{prefix}_*.json")):
        query = path.stem.replace(f"{prefix}_", "")
        print(f"📄 Обработка query='{query}' → {path.name}")

        pipeline_results = load_json(path) or []
        vacancies, resumes_by_id = _load_vacancies_and_resumes_classical(query)
        vacancies_by_id = {str(v.get("id")): v for v in vacancies}

        reranked_results = []

        for vac_entry in tqdm(pipeline_results, desc=f"Cross-encoder [classical-{method}] {query}"):
            pairs, selected_candidates = _build_pairs_for_vacancy_classical(
                vacancy_entry=vac_entry,
                vacancies_by_id=vacancies_by_id,
                resumes_by_id=resumes_by_id,
            )

            if not pairs:
                vac_entry_reranked = dict(vac_entry)
                vac_entry_reranked["cross_encoder_candidates"] = []
                reranked_results.append(vac_entry_reranked)
                continue

            scores = model.predict(pairs, batch_size=batch_size)

            for cand, s in zip(selected_candidates, scores):
                cand["rerank_score"] = float(s)
            selected_sorted = sorted(selected_candidates, key=lambda x: x["rerank_score"], reverse=True)

            vac_entry_reranked = dict(vac_entry)
            vac_entry_reranked["cross_encoder_candidates"] = selected_sorted
            reranked_results.append(vac_entry_reranked)

        name_part = f"cross_encoder_{method}_{model_key}_{query}" if model_key else f"cross_encoder_{method}_{query}"
        out_path = out_dir / f"{name_part}.json"
        save_json(out_path, reranked_results)
        print(f"✅ Сохранён cross-encoder rerank (classical) → {out_path}")

    print("🎯 Cross-encoder reranking (classical) завершён.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cross-encoder reranking поверх classical-pipeline (BM25 / TF-IDF)")
    parser.add_argument("--method", default="bm25", choices=("bm25", "tfidf"), help="Классический метод: bm25 или tfidf")
    parser.add_argument("--model", default="russian", choices=("russian", "minilm", "multilingual"), help="Cross-encoder: russian, minilm, multilingual")
    parser.add_argument("--model-name", default=None, help="Полное имя модели (перекрывает --model)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Размер батча (по умолчанию {DEFAULT_BATCH_SIZE})")
    args = parser.parse_args()
    run_cross_encoder_rerank_classical(method=args.method, model_name=args.model_name, model_key=args.model, batch_size=args.batch_size)

