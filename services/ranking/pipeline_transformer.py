"""
Pipeline ранжирования для transformer-данных (эмбеддинги).

Входные данные: готовые обработанные файлы
  - data/prepared/resumes/cleaned/transformer/resumes_<query>.json
  - data/prepared/vacancies/cleaned/transformer/vacancies_<query>.json

Эмбеддинги резюме считаются один раз на весь query; для каждой вакансии — только эмбеддинг вакансии.
Для E5 (intfloat/multilingual-e5-large) используются префиксы "query: " и "passage: "; для остальных моделей — нет.
"""
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util

from config.paths import (
    RESUMES_TRANSFORMER,       # data/prepared/resumes/cleaned/transformer
    VACANCIES_TRANSFORMER,    # data/prepared/vacancies/cleaned/transformer
    PIPELINE_TRANSFORMER_RESULTS,
    PIPELINE_STATS_DIR,
)
from services.utils import load_json, save_json
from services.ranking.experience_text import append_experience_to_resume_text, append_experience_to_vacancy_text
from services.ranking.pipeline_common import (
    run_pipeline_for_vacancy,
    compute_global_statistics,
)

# Модели как в существующих ранкерах (e5, minilm, ru_sbert, mpnet)
TRANSFORMER_MODELS = {
    "e5": "intfloat/multilingual-e5-large",
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "ru_sbert": "ai-forever/sbert_large_nlu_ru",
    "mpnet": "all-mpnet-base-v2",
}

# Только E5 требует префиксы для входа
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "


def _resume_text_for_embedding(resume: dict, use_e5_prefix: bool) -> str:
    """Текст резюме для эмбеддинга; для E5 добавляется префикс 'passage: '."""
    text = append_experience_to_resume_text(resume)
    if use_e5_prefix:
        return f"{E5_PASSAGE_PREFIX}{text}"
    return text


def _vacancy_text_for_embedding(vacancy: dict, use_e5_prefix: bool) -> str:
    """Текст вакансии для эмбеддинга; для E5 добавляется префикс 'query: '."""
    text = append_experience_to_vacancy_text(vacancy)
    if use_e5_prefix:
        return f"{E5_QUERY_PREFIX}{text}"
    return text


def make_similarity_getter(model: SentenceTransformer, resume_embeddings, use_e5_prefix: bool):
    """
    Возвращает функцию (vacancy, filtered_resumes, filtered_indices) -> list[float].
    Эмбеддинги резюме уже вычислены (resume_embeddings); для вакансии считаем только её эмбеддинг.
    """
    def get_similarity_scores(vacancy: dict, filtered_resumes: list, filtered_indices: list) -> list:
        if not filtered_resumes or not filtered_indices:
            return []
        vacancy_text = _vacancy_text_for_embedding(vacancy, use_e5_prefix)
        vac_emb = model.encode(vacancy_text, convert_to_tensor=True, normalize_embeddings=True)
        # Берём только эмбеддинги отфильтрованных по опыту резюме
        res_emb = resume_embeddings[filtered_indices]
        raw = util.cos_sim(vac_emb, res_emb).cpu().numpy().flatten()
        return raw.tolist()

    return get_similarity_scores


def run_pipeline_transformer(method: str = "e5"):
    """
    Запускает новый pipeline для transformer-данных.

    method: одна из "e5", "minilm", "ru_sbert", "mpnet" (те же модели, что в run.py rank).
    Эмбеддинги всех резюме считаются один раз на каждый query; для каждой вакансии — только embedding вакансии.
    Результаты: data/results/pipeline_transformer/<method>/pipeline_<method>_<query>.json
    Статистика: data/results/pipeline_stats/pipeline_<method>_<query>_stats.json
    """
    method = (method or "e5").strip().lower()
    if method not in TRANSFORMER_MODELS:
        raise ValueError(f"Неизвестная модель: {method}. Доступны: {list(TRANSFORMER_MODELS)}")

    use_e5_prefix = method == "e5"
    model_name = TRANSFORMER_MODELS[method]
    model = SentenceTransformer(model_name)

    out_dir = PIPELINE_TRANSFORMER_RESULTS / method
    out_dir.mkdir(parents=True, exist_ok=True)
    PIPELINE_STATS_DIR.mkdir(parents=True, exist_ok=True)

    for vacancy_file in sorted(VACANCIES_TRANSFORMER.glob("vacancies_*.json")):
        query = vacancy_file.stem.replace("vacancies_", "")
        resume_file = RESUMES_TRANSFORMER / f"resumes_{query}.json"
        if not resume_file.exists():
            print(f"[!] Нет резюме для query {query}, пропускаем")
            continue

        resumes = load_json(resume_file)
        vacancies = load_json(vacancy_file)
        resume_ids = [r["id"] for r in resumes]

        # Один раз считаем эмбеддинги всех резюме для этого query
        resume_texts = [_resume_text_for_embedding(r, use_e5_prefix) for r in resumes]
        resume_embeddings = model.encode(
            resume_texts, convert_to_tensor=True, normalize_embeddings=True
        )

        get_similarity = make_similarity_getter(model, resume_embeddings, use_e5_prefix)

        all_results = []
        for v in tqdm(vacancies, desc=f"Pipeline {method} [{query}]"):
            result = run_pipeline_for_vacancy(
                vacancy=v,
                resumes=resumes,
                resume_ids=resume_ids,
                get_similarity_scores=get_similarity,
            )
            all_results.append(result)

        out_path = out_dir / f"pipeline_{method}_{query}.json"
        save_json(out_path, all_results)
        print(f"[+] Pipeline {method} {query} → {out_path}")

        stats = compute_global_statistics(all_results)
        stats_path = PIPELINE_STATS_DIR / f"pipeline_{method}_{query}_stats.json"
        save_json(stats_path, stats)
        print(f"[+] Статистика → {stats_path}")

    print(f"[+] Pipeline transformer ({method}) завершён.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--method", default="e5", choices=list(TRANSFORMER_MODELS), help="e5, minilm, ru_sbert, mpnet")
    args = p.parse_args()
    run_pipeline_transformer(method=args.method)
