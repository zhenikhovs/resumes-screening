import json
from pathlib import Path
from tqdm import tqdm
import numpy as np
from sentence_transformers import SentenceTransformer, util
from num2words import num2words

# --- Пути ---
resumes_folder = Path("../data/prepared/resumes/cleaned/transformer/")
vacancies_folder = Path("../data/prepared/vacancies/cleaned/transformer/")
output_folder = Path("../data/results/e5_results/")
output_folder.mkdir(parents=True, exist_ok=True)

# --- Модель ---
model_name = "intfloat/multilingual-e5-large"
model = SentenceTransformer(model_name)

# --- Загрузка JSON ---
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Перевод числа в слова на русском ---
def number_to_words_ru(num: int) -> str:
    try:
        num = int(num)
        return num2words(num, lang="ru")
    except:
        return "ноль"

# --- Склонение слова "месяц" ---
def month_declension(num: int) -> str:
    num = abs(int(num))
    if 11 <= num % 100 <= 14:
        return "месяцев"
    if num % 10 == 1:
        return "месяц"
    if 2 <= num % 10 <= 4:
        return "месяца"
    return "месяцев"

# --- Добавляем опыт в текст резюме ---
def append_experience_to_resume_text(resume: dict) -> str:
    total_exp = resume.get("total_experience_months", 0)
    try:
        total_exp = int(total_exp)
    except:
        total_exp = 0

    exp_words = number_to_words_ru(total_exp)
    decl = month_declension(total_exp)
    return f"{resume['text']}\nОпыт: {exp_words} {decl}"

# --- Добавляем опыт в текст вакансии ---
def append_experience_to_vacancy_text(vacancy: dict) -> str:
    min_exp = vacancy.get("min_experience_months")
    max_exp = vacancy.get("max_experience_months")

    def safe_int(val):
        try:
            return int(val)
        except:
            return 0

    if min_exp is not None:
        min_exp = safe_int(min_exp)
    if max_exp is not None:
        max_exp = safe_int(max_exp)

    if min_exp is not None and max_exp is not None:
        min_words = number_to_words_ru(min_exp)
        max_words = number_to_words_ru(max_exp)
        return f"{vacancy['text']}\nТребуемый опыт: от {min_words} до {max_words} месяцев"
    elif min_exp is not None:
        min_words = number_to_words_ru(min_exp)
        return f"{vacancy['text']}\nТребуемый опыт: от {min_words} месяцев"
    else:
        return f"{vacancy['text']}\nТребуемый опыт: не указан"

# --- Обработка ---
for vacancy_file in vacancies_folder.glob("vacancies_*.json"):
    query = vacancy_file.stem.replace("vacancies_", "")
    resume_file = resumes_folder / f"resumes_{query}.json"

    if not resume_file.exists():
        print(f"[!] Нет резюме для query {query}, пропускаем")
        continue

    vacancies = load_json(vacancy_file)
    resumes = load_json(resume_file)

    resume_ids = [r["id"] for r in resumes]

    # --- Формируем тексты с опытом ---
    resume_texts = [append_experience_to_resume_text(r) for r in resumes]
    resume_embeddings = model.encode(resume_texts, convert_to_tensor=True)

    results = []

    for v in tqdm(vacancies, desc=f"Ranking vacancies [{query}]"):
        vacancy_text = append_experience_to_vacancy_text(v)
        vacancy_embedding = model.encode(vacancy_text, convert_to_tensor=True)

        # --- Косинусное сходство ---
        scores = util.cos_sim(vacancy_embedding, resume_embeddings).cpu().numpy().flatten()

        candidates = [
            {
                "resume_id": resume_ids[i],
                "score": round(float(scores[i]), 4)
            }
            for i in range(len(resumes))
        ]

        candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)

        results.append({
            "vacancy_id": v["id"],
            "candidates": candidates_sorted
        })

    # --- Сохранение ---
    out_path = output_folder / f"e5_{query}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[+] Query {query} обработан → {out_path}")
