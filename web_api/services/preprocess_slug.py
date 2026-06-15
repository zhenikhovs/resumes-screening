"""Pre-clean и clean для одного slug (camp_{id})."""
from services.preprocessing.clean_resumes import (
    process_resume_classical,
    process_resume_transformer,
)
from services.preprocessing.clean_vacancies import build_vacancy_classical, build_vacancy_transformer
from services.preprocessing.pre_clean_resumes import clean_resume as pre_clean_resume
from services.preprocessing.pre_clean_vacancies import clean_vacancy as pre_clean_vacancy
from services.utils import load_json, save_json
from config.paths import (
    PRE_CLEANED_RESUMES,
    PRE_CLEANED_VACANCIES,
    RAW_FULL_RESUMES,
    RAW_FULL_VACANCIES,
    RESUMES_CLASSICAL,
    RESUMES_TRANSFORMER,
    VACANCIES_CLASSICAL,
    VACANCIES_TRANSFORMER,
)


def pre_clean_and_clean_slug(slug: str) -> dict:
    """Полный цикл pre-clean → classical/transformer для resumes_{slug} и vacancies_{slug}."""
    res_full = RAW_FULL_RESUMES / f"resumes_{slug}.json"
    vac_full = RAW_FULL_VACANCIES / f"vacancies_{slug}.json"

    if not res_full.exists():
        raise FileNotFoundError(f"Нет файла резюме: {res_full}")
    if not vac_full.exists():
        raise FileNotFoundError(f"Нет файла вакансий: {vac_full}")

    raw_resumes = load_json(res_full) or []
    raw_vacancies = load_json(vac_full) or []

    pre_res = [pre_clean_resume(r) for r in raw_resumes]
    pre_vac = [pre_clean_vacancy(v) for v in raw_vacancies]
    for r in pre_res:
        r["query"] = slug.replace("_", " ")
    for v in pre_vac:
        v["query"] = slug.replace("_", " ")

    PRE_CLEANED_RESUMES.mkdir(parents=True, exist_ok=True)
    PRE_CLEANED_VACANCIES.mkdir(parents=True, exist_ok=True)
    save_json(PRE_CLEANED_RESUMES / f"resumes_{slug}.json", pre_res)
    save_json(PRE_CLEANED_VACANCIES / f"vacancies_{slug}.json", pre_vac)

    classical_r, transformer_r = [], []
    for r in pre_res:
        classical_r.append(process_resume_classical(r))
        transformer_r.append(process_resume_transformer(r))

    classical_v, transformer_v = [], []
    for v in pre_vac:
        classical_v.append(build_vacancy_classical(v))
        transformer_v.append(build_vacancy_transformer(v))

    RESUMES_CLASSICAL.mkdir(parents=True, exist_ok=True)
    RESUMES_TRANSFORMER.mkdir(parents=True, exist_ok=True)
    VACANCIES_CLASSICAL.mkdir(parents=True, exist_ok=True)
    VACANCIES_TRANSFORMER.mkdir(parents=True, exist_ok=True)

    save_json(RESUMES_CLASSICAL / f"resumes_{slug}.json", classical_r)
    save_json(RESUMES_TRANSFORMER / f"resumes_{slug}.json", transformer_r)
    save_json(VACANCIES_CLASSICAL / f"vacancies_{slug}.json", classical_v)
    save_json(VACANCIES_TRANSFORMER / f"vacancies_{slug}.json", transformer_v)

    return {
        "resumes": len(classical_r),
        "vacancies": len(classical_v),
    }
