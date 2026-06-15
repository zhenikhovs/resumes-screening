"""Ранжирование эмбеддингами MPnet. Score per-vacancy min-max → [0, 1]."""
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util

from config.paths import RESUMES_TRANSFORMER, VACANCIES_TRANSFORMER, MPNET_RESULTS
from services.utils import load_json, save_json
from services.ranking.experience_text import append_experience_to_resume_text, append_experience_to_vacancy_text
from services.ranking.score_utils import normalize_scores

MPNET_RESULTS.mkdir(parents=True, exist_ok=True)
model = SentenceTransformer("all-mpnet-base-v2")


def run_mpnet():
    for vacancy_file in sorted(VACANCIES_TRANSFORMER.glob("vacancies_*.json")):
        query = vacancy_file.stem.replace("vacancies_", "")
        resume_file = RESUMES_TRANSFORMER / f"resumes_{query}.json"
        if not resume_file.exists():
            print(f"[!] Нет резюме для query {query}, пропускаем")
            continue

        vacancies = load_json(vacancy_file)
        resumes = load_json(resume_file)
        resume_ids = [r["id"] for r in resumes]
        resume_texts = [append_experience_to_resume_text(r) for r in resumes]
        resume_embeddings = model.encode(resume_texts, convert_to_tensor=True, normalize_embeddings=True)

        results = []
        for v in tqdm(vacancies, desc=f"MPnet [{query}]"):
            vacancy_text = append_experience_to_vacancy_text(v)
            vacancy_embedding = model.encode(vacancy_text, convert_to_tensor=True, normalize_embeddings=True)
            raw_scores = util.cos_sim(vacancy_embedding, resume_embeddings).cpu().numpy().flatten()
            final_scores = normalize_scores(raw_scores.tolist())
            candidates = [{"resume_id": resume_ids[i], "score": round(final_scores[i], 4)} for i in range(len(resumes))]
            results.append({"vacancy_id": v["id"], "candidates": sorted(candidates, key=lambda x: x["score"], reverse=True)})

        save_json(MPNET_RESULTS / f"mpnet_{query}.json", results)
        print(f"[+] MPnet {query} → {MPNET_RESULTS / f'mpnet_{query}.json'}")


if __name__ == "__main__":
    run_mpnet()
