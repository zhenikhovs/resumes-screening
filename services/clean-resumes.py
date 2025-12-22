import json
from pathlib import Path
from services.normalization.tech_aliases import TECH_ALIASES
import re

PRE_CLEANED_DIR = Path("../data/prepared/resumes/pre-cleaned")
OUT_DIR = Path("../data/prepared/resumes/cleaned")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_tech(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    for pattern, repl in TECH_ALIASES.items():
        text = re.sub(pattern, repl, text)
    return text


def build_text_title(resume: dict) -> str:
    parts = []

    if resume.get("title"):
        parts.append(resume["title"])

    for r in resume.get("professional_roles", []):
        parts.append(r["name"])

    for e in resume.get("experience", []):
        if e.get("position"):
            parts.append(e["position"])

    return " | ".join(dict.fromkeys(parts))


def build_text_skills(resume: dict) -> str:
    parts = []

    if resume.get("skills"):
        parts.append(resume["skills"])

    if resume.get("skill_set"):
        parts.extend(resume["skill_set"])

    text = " ".join(parts)
    return normalize_tech(text)


def build_text_experience(resume: dict) -> str:
    total_exp = resume.get("total_experience") or {}
    months = total_exp.get("months")

    exp_years = ""
    if months:
        years = months // 12
        exp_years = f"Total experience: {years} years."

    positions = []
    for exp in resume.get("experience") or []:
        pos = exp.get("position")
        if pos:
            positions.append(pos)

    positions = list(dict.fromkeys(positions))  # unique, keep order

    return " ".join(filter(None, [
        exp_years,
        "Positions: " + ", ".join(positions) if positions else ""
    ]))


def build_text_education(resume: dict) -> str:
    parts = []

    edu = resume.get("education", {})
    for p in edu.get("primary", []):
        parts.append(f"{p.get('organization')} {p.get('result')}")

    for a in edu.get("additional", []):
        parts.append(f"{a.get('name')}")

    return " ".join(parts)


def build_meta(resume: dict) -> dict:
    total_exp = resume.get("total_experience") or {}

    languages = []
    for l in resume.get("language") or []:
        lang_id = l.get("id")
        level_id = (l.get("level") or {}).get("id")
        if lang_id and level_id:
            languages.append(f"{lang_id}:{level_id}")

    return {
        "city": (resume.get("area") or {}).get("name"),
        "total_experience_months": total_exp.get("months"),
        "employment": (resume.get("employment") or {}).get("name"),
        "schedule": (resume.get("schedule") or {}).get("name"),
        "languages": languages
    }



def clean_resume(resume: dict) -> dict:
    return {
        "id": resume.get("id"),

        "meta": build_meta(resume),

        "text_title": build_text_title(resume),
        "text_skills": build_text_skills(resume),
        "text_experience": build_text_experience(resume),
        "text_education": build_text_education(resume),
    }


def process_files():
    for file_path in PRE_CLEANED_DIR.glob("resumes_*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cleaned = [clean_resume(r) for r in data]

        out_path = OUT_DIR / file_path.name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

        print(f"✅ {file_path.name} → cleaned ({len(cleaned)})")


if __name__ == "__main__":
    process_files()
