"""
Второй этап ранжирования: reranking с помощью cross-encoder поверх результатов transformer-pipeline.

1. Берём результаты первого этапа:
   data/results/pipeline_transformer/<method>/pipeline_<method>_<query>.json
2. Для каждой вакансии:
   - берём только тех кандидатов, у кого score_norm >= threshold (т.е. прошли dynamic threshold);
   - по resume_id находим текст резюме в data/prepared/resumes/cleaned/transformer/resumes_<query>.json;
   - формируем пары (vacancy_text, resume_text);
   - прогоняем через cross-encoder батчами (batch_size по умолчанию 32);
   - добавляем rerank_score и пересортировываем кандидатов по нему (по убыванию).
3. Сохраняем результат в:
   data/results/pipeline_cross_encoder/<method>/cross_encoder_<method>_<query>.json
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm
from sentence_transformers import CrossEncoder

from config.paths import (
    RESUMES_TRANSFORMER,
    VACANCIES_TRANSFORMER,
    PIPELINE_TRANSFORMER_RESULTS,
    PIPELINE_CROSS_ENCODER_RESULTS,
)
from services.utils import load_json, save_json
from services.ranking.experience_text import (
    append_experience_to_resume_text,
    append_experience_to_vacancy_text,
)

# Набор моделей для сравнения: русская, лёгкая, мультиязычная
# multilingual: старый cross-encoder/ms-marco-Multilingual-MiniLM-L12-v2 отдаёт 401 — используем публичный аналог
CROSS_ENCODER_MODELS = {
    "russian": "DiTy/cross-encoder-russian-msmarco",           # для русского текста
    "minilm": "cross-encoder/ms-marco-MiniLM-L-6-v2",         # лёгкая, быстрая
    "multilingual": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",  # мультиязычная (mMARCO, 13 языков)
}
DEFAULT_CROSS_ENCODER_MODEL = CROSS_ENCODER_MODELS["russian"]
DEFAULT_BATCH_SIZE = 32


def _load_vacancies_and_resumes(query: str) -> Tuple[list, dict]:
    """Загружает вакансии и резюме для заданного query, возвращает (vacancies, resumes_by_id)."""
    vac_path = VACANCIES_TRANSFORMER / f"vacancies_{query}.json"
    res_path = RESUMES_TRANSFORMER / f"resumes_{query}.json"
    vacancies = load_json(vac_path) or []
    resumes = load_json(res_path) or []
    resumes_by_id = {str(r.get("id")): r for r in resumes}
    return vacancies, resumes_by_id


def _build_pairs_for_vacancy(
    vacancy_entry: dict,
    vacancies_by_id: dict,
    resumes_by_id: dict,
) -> Tuple[List[Tuple[str, str]], List[dict]]:
    """
    Для одной вакансии из pipeline-результатов строит пары (vacancy_text, resume_text)
    только для кандидатов с score_norm >= threshold.

    Возвращает:
      - pairs: список (vacancy_text, resume_text)
      - candidates: список словарей-кандидатов (будем в них добавлять rerank_score)
    """
    vid = str(vacancy_entry.get("vacancy_id"))
    threshold = vacancy_entry.get("threshold")
    candidates_all = vacancy_entry.get("candidates") or []

    # Вакансия из исходного transformer-корпуса
    v_src = vacancies_by_id.get(vid)
    if not v_src:
        return [], []

    vacancy_text = append_experience_to_vacancy_text(v_src)

    pairs: List[Tuple[str, str]] = []
    selected_candidates: List[dict] = []

    for c in candidates_all:
        if threshold is not None and c.get("score_norm", 0.0) < threshold:
            continue
        rid = str(c.get("resume_id"))
        r_src = resumes_by_id.get(rid)
        if not r_src:
            continue
        resume_text = append_experience_to_resume_text(r_src, for_rerank=True)
        pairs.append((vacancy_text, resume_text))
        selected_candidates.append(c)

    return pairs, selected_candidates


def run_cross_encoder_rerank(
    method: str = "e5",
    model_name: str | None = None,
    model_key: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    """
    Запускает второй этап ранжирования для указанного transformer-метода.

    method: один из e5, minilm, ru_sbert, mpnet (подразумевается, что для него уже есть
            файлы pipeline_<method>_<query>.json в data/results/pipeline_transformer/<method>/).
    model_name: полное имя cross-encoder модели (если None, берётся из model_key или default).
    model_key: ключ из CROSS_ENCODER_MODELS (russian, minilm, multilingual); используется в имени файла.
    batch_size: размер батча для предсказаний (32 или 64).
    """
    method = (method or "e5").strip().lower()
    if model_key and model_key in CROSS_ENCODER_MODELS:
        name = CROSS_ENCODER_MODELS[model_key]
        if model_name is None:
            model_name = name
    elif model_name is None:
        model_name = DEFAULT_CROSS_ENCODER_MODEL
        model_key = model_key or "russian"

    in_dir = PIPELINE_TRANSFORMER_RESULTS / method
    if not in_dir.exists():
        print(f"❌ Нет директории с результатами transformer-pipeline для метода {method}: {in_dir}")
        return

    out_dir = PIPELINE_CROSS_ENCODER_RESULTS / method
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔁 Cross-encoder reranking: method={method}, model={model_name}, batch_size={batch_size}")
    model = CrossEncoder(model_name)

    for path in sorted(in_dir.glob(f"pipeline_{method}_*.json")):
        query = path.stem.replace(f"pipeline_{method}_", "")
        print(f"📄 Обработка query='{query}' → {path.name}")

        pipeline_results = load_json(path) or []
        vacancies, resumes_by_id = _load_vacancies_and_resumes(query)
        vacancies_by_id = {str(v.get("id")): v for v in vacancies}

        reranked_results = []

        for vac_entry in tqdm(pipeline_results, desc=f"Cross-encoder [{method}] {query}"):
            # Строим пары только по кандидатам выше threshold
            pairs, selected_candidates = _build_pairs_for_vacancy(
                vacancy_entry=vac_entry,
                vacancies_by_id=vacancies_by_id,
                resumes_by_id=resumes_by_id,
            )

            if not pairs:
                # Кандидатов выше threshold нет — переносим запись как есть, с пустым rerank-массивом
                vac_entry_reranked = dict(vac_entry)
                vac_entry_reranked["cross_encoder_candidates"] = []
                reranked_results.append(vac_entry_reranked)
                continue

            # Предсказания cross-encoder батчами
            scores = model.predict(pairs, batch_size=batch_size)

            # Добавляем rerank_score к кандидатам и сортируем
            for cand, s in zip(selected_candidates, scores):
                cand["rerank_score"] = float(s)
            selected_sorted = sorted(selected_candidates, key=lambda x: x["rerank_score"], reverse=True)

            vac_entry_reranked = dict(vac_entry)
            vac_entry_reranked["cross_encoder_candidates"] = selected_sorted
            reranked_results.append(vac_entry_reranked)

        name_part = f"cross_encoder_{method}_{model_key}_{query}" if model_key else f"cross_encoder_{method}_{query}"
        out_path = out_dir / f"{name_part}.json"
        save_json(out_path, reranked_results)
        print(f"✅ Сохранён cross-encoder rerank → {out_path}")

    print("🎯 Cross-encoder reranking завершён.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cross-encoder reranking поверх transformer-pipeline")
    parser.add_argument("--method", default="e5", help="Transformer-метод: e5, minilm, ru_sbert, mpnet")
    parser.add_argument("--model", default="russian", choices=("russian", "minilm", "multilingual"), help="Cross-encoder: russian, minilm, multilingual")
    parser.add_argument("--model-name", default=None, help="Полное имя модели (перекрывает --model)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Размер батча (по умолчанию {DEFAULT_BATCH_SIZE})")
    args = parser.parse_args()
    run_cross_encoder_rerank(method=args.method, model_name=args.model_name, model_key=args.model, batch_size=args.batch_size)

