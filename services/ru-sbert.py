import json
from pathlib import Path
from tqdm import tqdm
import numpy as np
from sentence_transformers import SentenceTransformer, util

# --- Пути ---
resumes_folder = Path("../data/prepared/resumes/cleaned/transformer/")
vacancies_folder = Path("../data/prepared/vacancies/cleaned/transformer/")
output_folder = Path("../data/results/rusbert_results/")
output_folder.mkdir(parents=True, exist_ok=True)

# --- Модель ---
model_name = "ai-forever/sbert_large_nlu_ru"
model = SentenceTransformer(model_name)

# --- Вес опыта в месяцах относительно текста ---
EXPERIENCE_WEIGHT = 0.17

# --- Загрузка JSON ---
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Обработка вакансий ---
for vacancy_file in vacancies_folder.glob("vacancies_*.json"):
    query = vacancy_file.stem.replace("vacancies_", "")
    resume_file = resumes_folder / f"resumes_{query}.json"

    if not resume_file.exists():
        print(f"[!] Нет резюме для query {query}, пропускаем")
        continue

    vacancies = load_json(vacancy_file)
    resumes = load_json(resume_file)

    resume_ids = [r["id"] for r in resumes]

    # --- Эмбеддинги резюме ---
    resume_texts = [r["text"] for r in resumes]
    resume_embeddings = model.encode(resume_texts, convert_to_tensor=True)

    results = []

    for v in tqdm(vacancies, desc=f"Ranking vacancies [{query}]"):
        vacancy_text = v["text"]
        vacancy_embedding = model.encode(vacancy_text, convert_to_tensor=True)

        # --- Text similarity (cosine) ---
        text_scores = util.cos_sim(
            vacancy_embedding,
            resume_embeddings
        ).cpu().numpy().flatten()

        # --- Опыт в месяцах ---
        exp_scores = []
        min_exp = v.get("min_experience_months")
        max_exp = v.get("max_experience_months")
        for r in resumes:
            try:
                total_exp = int(r.get("total_experience_months", 0))
            except:
                total_exp = 0
            score = 0.0
            if min_exp is not None:
                try:
                    min_exp_int = int(min_exp)
                except:
                    min_exp_int = 0
                if total_exp >= min_exp_int:
                    if max_exp is None:
                        score = 1.0
                    else:
                        try:
                            max_exp_int = int(max_exp)
                        except:
                            max_exp_int = total_exp
                        if total_exp <= max_exp_int:
                            score = 1.0
            exp_scores.append(score)
        exp_scores = np.array(exp_scores) * EXPERIENCE_WEIGHT

        # --- Финальный score (clip для диапазона [0,1]) ---
        final_scores = np.clip(text_scores + exp_scores, 0, 1).tolist()

        candidates = [
            {
                "resume_id": resume_ids[i],
                "score": round(final_scores[i], 4),
                "text_score": round(float(text_scores[i]), 4),
                "experience_bonus": round(float(exp_scores[i]), 4)
            }
            for i in range(len(resumes))
        ]

        candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)

        results.append({
            "vacancy_id": v["id"],
            "candidates": candidates_sorted
        })

    # --- Сохранение ---
    out_path = output_folder / f"rusbert_{query}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[+] Query {query} обработан → {out_path}")
