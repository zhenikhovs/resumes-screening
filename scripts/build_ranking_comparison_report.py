#!/usr/bin/env python3
"""
Собирает отчёт сравнения ранжирования: по каждому запросу 2+ вакансии,
для каждой вакансии — топ-3 резюме по каждому методу (bm25, tfidf, e5, minilm, mpnet, ru_sbert).
Выход: data/results/RANKING_COMPARISON_BY_VACANCY.md (единственная копия)

Чтобы в отчёте был блок tfidf, сначала сгенерируйте pipeline TF-IDF:
  python run.py pipeline_ranking --classical
(создаёт и pipeline_classical_*.json (BM25), и pipeline_tfidf_*.json (TF-IDF)).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data"
RESULTS = DATA / "results"
PIPELINE_CLASSICAL = RESULTS / "pipeline_classical"
PIPELINE_TRANSFORMER = RESULTS / "pipeline_transformer"
VACANCIES_DIR = DATA / "prepared" / "vacancies" / "cleaned" / "transformer"
RESUMES_DIR = DATA / "prepared" / "resumes" / "cleaned" / "transformer"

QUERIES = ["backend_developer", "frontend_developer", "fullstack_developer"]
VACANCIES_PER_QUERY = 2
TOP_K = 3
VACANCY_TEXT_MAX = 500
RESUME_TEXT_MAX = 350

METHODS = [
    ("bm25", PIPELINE_CLASSICAL / "pipeline_classical_{query}.json"),   # classical BM25
    ("tfidf", PIPELINE_CLASSICAL / "pipeline_tfidf_{query}.json"),       # classical TF-IDF
    ("e5", PIPELINE_TRANSFORMER / "e5" / "pipeline_e5_{query}.json"),
    ("minilm", PIPELINE_TRANSFORMER / "minilm" / "pipeline_minilm_{query}.json"),
    ("mpnet", PIPELINE_TRANSFORMER / "mpnet" / "pipeline_mpnet_{query}.json"),
    ("ru_sbert", PIPELINE_TRANSFORMER / "ru_sbert" / "pipeline_ru_sbert_{query}.json"),
]


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def short_text(text: str, max_len: int) -> str:
    if not text:
        return ""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def main():
    out_path = RESULTS / "RANKING_COMPARISON_BY_VACANCY.md"
    lines = []
    lines.append("# Сравнение ранжирования по запросам и вакансиям")
    lines.append("")
    lines.append("Для каждого запроса приведены 2 вакансии. Для каждой вакансии — топ-3 кандидата по каждому методу (bm25, tfidf, e5, minilm, mpnet, ru_sbert).")
    lines.append("")
    lines.append("---")
    lines.append("")

    for query in QUERIES:
        vac_path = VACANCIES_DIR / f"vacancies_{query}.json"
        res_path = RESUMES_DIR / f"resumes_{query}.json"
        vacancies = load_json(vac_path)
        resumes_list = load_json(res_path)
        if not vacancies or not resumes_list:
            lines.append(f"## Запрос: {query}")
            lines.append("")
            lines.append("*(данные не найдены)*")
            lines.append("")
            continue

        resumes_by_id = {str(r.get("id")): r for r in resumes_list}

        # Загрузить результаты по всем методам для этого query
        method_data = {}
        for method_name, path_tpl in METHODS:
            path = Path(str(path_tpl).format(query=query))
            data = load_json(path)
            if data is not None:
                method_data[method_name] = data

        if not method_data:
            lines.append(f"## Запрос: {query}")
            lines.append("")
            lines.append("*(нет результатов ранжирования)*")
            lines.append("")
            continue

        lines.append(f"# Запрос: {query}")
        lines.append("")

        for vac_idx in range(min(VACANCIES_PER_QUERY, len(vacancies))):
            vac = vacancies[vac_idx]
            vac_id = vac.get("id") or vac.get("vacancy_id")
            vac_text = short_text(vac.get("text", ""), VACANCY_TEXT_MAX)

            lines.append(f"## Вакансия {vac_idx + 1} (id={vac_id})")
            lines.append("")
            lines.append("**Текст вакансии:**")
            lines.append("")
            lines.append(vac_text)
            lines.append("")
            lines.append("---")
            lines.append("")

            for method_name, pipeline in method_data.items():
                if vac_idx >= len(pipeline):
                    continue
                vacancy_block = pipeline[vac_idx]
                cands = (vacancy_block.get("candidates") or [])[:TOP_K]
                rids = [str(c.get("resume_id")) for c in cands if c.get("resume_id") is not None]

                lines.append(f"### Метод: {method_name} — топ-{TOP_K} резюме")
                lines.append("")
                for i, rid in enumerate(rids, 1):
                    r = resumes_by_id.get(rid)
                    if r:
                        pos = (r.get("text") or "").strip()
                        pos = short_text(pos, RESUME_TEXT_MAX)
                        lines.append(f"{i}. **{rid[:24]}...**  \n   {pos}")
                    else:
                        lines.append(f"{i}. **{rid[:24]}...**  \n   *(резюме не найдено в выборке)*")
                    lines.append("")
                lines.append("")

        lines.append("---")
        lines.append("")

    text = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Отчёт: {out_path}")


if __name__ == "__main__":
    main()
