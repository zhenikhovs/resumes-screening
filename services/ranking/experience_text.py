"""Дописывание стажа в месяцах к тексту для transformer-пайплайна (не для classical)."""
from num2words import num2words


def _safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def number_to_words_ru(num: int) -> str:
    try:
        return num2words(int(num), lang="ru")
    except (TypeError, ValueError):
        return "ноль"


def month_declension(num: int) -> str:
    num = abs(int(num))
    if 11 <= num % 100 <= 14:
        return "месяцев"
    if num % 10 == 1:
        return "месяц"
    if 2 <= num % 10 <= 4:
        return "месяца"
    return "месяцев"


def _resume_base_text(resume: dict, for_rerank: bool = False) -> str:
    if for_rerank and resume.get("text_rerank"):
        return resume["text_rerank"]
    return resume.get("text", "")


def append_experience_to_resume_text(resume: dict, for_rerank: bool = False) -> str:
    """Только transformer: к text или text_rerank дописывается суммарный стаж словами."""
    total_exp = _safe_int(resume.get("total_experience_months", 0))
    base_text = _resume_base_text(resume, for_rerank=for_rerank)
    return f"{base_text}\nОпыт: {number_to_words_ru(total_exp)} {month_declension(total_exp)}"


def append_experience_to_vacancy_text(vacancy: dict) -> str:
    """Только transformer: к text вакансии дописывается требуемый стаж."""
    min_exp_raw = vacancy.get("min_experience_months")
    max_exp_raw = vacancy.get("max_experience_months")
    min_exp = _safe_int(min_exp_raw) if min_exp_raw is not None else None
    max_exp = _safe_int(max_exp_raw) if max_exp_raw is not None else None
    if min_exp is not None and max_exp is not None:
        exp_text = f"Требуемый опыт: от {number_to_words_ru(min_exp)} до {number_to_words_ru(max_exp)} месяцев"
    elif min_exp is not None:
        exp_text = f"Требуемый опыт: от {number_to_words_ru(min_exp)} {month_declension(min_exp)}"
    else:
        exp_text = "Требуемый опыт: не указан"
    return f"{vacancy.get('text', '')}\n{exp_text}"
