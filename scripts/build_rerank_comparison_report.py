#!/usr/bin/env python3
"""До/после cross-encoder: data/results/RERANK_COMPARISON_BY_VACANCY.md + rerank_top1_shift_stats.json"""
import json
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data"
RESULTS = DATA / "results"
CE_ROOT = RESULTS / "pipeline_cross_encoder"

QUERIES = ["backend_developer", "frontend_developer", "fullstack_developer"]
VACANCIES_PER_QUERY = 2
TOP_K = 3
RESUME_SNIP = 320

RETRIEVAL_ORDER = ("ru_sbert", "minilm", "mpnet", "e5", "bm25", "tfidf")
CE_ORDER = ("multilingual", "minilm", "russian")


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def short_text(text: str, max_len: int) -> str:
    if not text:
        return ""
    t = text.strip().replace("\n", " ")
    return t[: max_len - 3].rsplit(" ", 1)[0] + "..." if len(t) > max_len else t


def parse_stem(stem: str):
    if not stem.startswith("cross_encoder_"):
        return None
    s = stem[len("cross_encoder_") :]
    for ret in RETRIEVAL_ORDER:
        if s.startswith(ret + "_"):
            rest = s[len(ret) + 1 :]
            for ce in CE_ORDER:
                if rest.startswith(ce + "_"):
                    return ret, ce, rest[len(ce) + 1 :]
            return None
    return None


def pipeline_path(retrieval: str, query: str) -> Path | None:
    if retrieval == "bm25":
        p = RESULTS / "pipeline_classical" / f"pipeline_classical_{query}.json"
    elif retrieval == "tfidf":
        p = RESULTS / "pipeline_classical" / f"pipeline_tfidf_{query}.json"
    else:
        p = RESULTS / "pipeline_transformer" / retrieval / f"pipeline_{retrieval}_{query}.json"
    return p if p.exists() else None


def resumes_path(retrieval: str, query: str) -> Path:
    if retrieval in ("bm25", "tfidf"):
        return DATA / "prepared" / "resumes" / "cleaned" / "classical" / f"resumes_{query}.json"
    return DATA / "prepared" / "resumes" / "cleaned" / "transformer" / f"resumes_{query}.json"


def snippet(resumes_by_id: dict, rid: str) -> str:
    r = resumes_by_id.get(str(rid))
    if not r:
        return "(нет)"
    if r.get("text"):
        return short_text(str(r["text"]), RESUME_SNIP)
    return short_text(f"{r.get('title', '')}. {r.get('skills', '')}", RESUME_SNIP)


def top_before(pipe_v: dict):
    th = pipe_v.get("threshold")
    c = [x for x in (pipe_v.get("candidates") or []) if th is None or x.get("score_norm", 0) >= th]
    c.sort(key=lambda x: x.get("score_norm", 0), reverse=True)
    return c[:TOP_K]


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Сравнение: до cross-encoder и после",
        "",
        "**До:** топ-3 в пуле кандидатов с score_norm ≥ threshold, по убыванию score_norm.",
        "**После:** топ-3 из cross_encoder_candidates по rerank_score.",
        "",
    ]
    stats = {"by_retrieval_ce": {}}

    discovered = []
    if CE_ROOT.exists():
        for sub in CE_ROOT.iterdir():
            if sub.is_dir():
                for path in sub.glob("cross_encoder_*.json"):
                    p = parse_stem(path.stem)
                    if p:
                        discovered.append((path, p[0], p[1], p[2]))

    if not discovered:
        lines += [
            "## Нет файлов cross-encoder",
            "Ожидаются JSON в `data/results/pipeline_cross_encoder/`.",
        ]
        stats["note"] = "no_files"
    else:
        grouped = defaultdict(list)
        for path, ret, ce, q in discovered:
            grouped[(ret, ce)].append((path, q))

        for (retrieval, ce_key), plist in sorted(grouped.items()):
            ks = {"n_vacancies": 0, "top1_changed": 0}
            jac_sum, jac_n = 0.0, 0
            lines += ["---", "", f"# Retrieval: **{retrieval}** · CE: **{ce_key}**", ""]

            for query in QUERIES:
                ce_path = next((p for p, q in plist if q == query), None)
                if not ce_path:
                    continue
                pp = pipeline_path(retrieval, query)
                if not pp:
                    continue
                ce_d = load_json(ce_path) or []
                pipe_d = load_json(pp) or []
                res = load_json(resumes_path(retrieval, query)) or []
                by_id = {str(r.get("id")): r for r in res}

                lines += [f"## Запрос: `{query}`", ""]
                shown = 0
                for ce_v in ce_d:
                    if shown >= VACANCIES_PER_QUERY:
                        break
                    vid = ce_v.get("vacancy_id")
                    pipe_v = next((x for x in pipe_d if str(x.get("vacancy_id")) == str(vid)), None)
                    if not pipe_v:
                        continue
                    shown += 1
                    before = top_before(pipe_v)
                    after = (ce_v.get("cross_encoder_candidates") or [])[:TOP_K]
                    b_ids = [str(c.get("resume_id")) for c in before]
                    a_ids = [str(c.get("resume_id")) for c in after]
                    ks["n_vacancies"] += 1
                    if b_ids and a_ids and b_ids[0] != a_ids[0]:
                        ks["top1_changed"] += 1
                    sb, sa = set(b_ids), set(a_ids)
                    if sb or sa:
                        jac_sum += len(sb & sa) / max(len(sb | sa), 1)
                        jac_n += 1

                    lines += [
                        f"### Вакансия {shown} (id={vid})",
                        "",
                        "#### До rerank",
                        "",
                    ]
                    for i, c in enumerate(before, 1):
                        rid = str(c.get("resume_id"))
                        lines += [
                            f"{i}. `{rid[:28]}...` score_norm={c.get('score_norm', 0):.4f}",
                            f"   {snippet(by_id, rid)}",
                            "",
                        ]
                    lines += ["#### После rerank", ""]
                    if not after:
                        lines += ["*(пусто)*", ""]
                    else:
                        for i, c in enumerate(after, 1):
                            rid = str(c.get("resume_id"))
                            lines += [
                                f"{i}. `{rid[:28]}...` rerank_score={float(c.get('rerank_score', 0)):.4f}",
                                f"   {snippet(by_id, rid)}",
                                "",
                            ]
                lines.append("")

            if ks["n_vacancies"]:
                ks["top1_change_rate"] = round(ks["top1_changed"] / ks["n_vacancies"], 4)
            if jac_n:
                ks["avg_jaccard_top3"] = round(jac_sum / jac_n, 4)
            stats["by_retrieval_ce"][f"{retrieval}_{ce_key}"] = ks

        lines += [
            "---",
            "",
            "## Показатели в rerank_top1_shift_stats.json",
            "- **top1_change_rate** — доля вакансий, где лидер до и после CE разный.",
            "- **avg_jaccard_top3** — среднее пересечение топ-3 до/после.",
            "",
        ]

    stats["source_dir"] = str(CE_ROOT)
    rerank_md = RESULTS / "RERANK_COMPARISON_BY_VACANCY.md"
    rerank_md.write_text("\n".join(lines), encoding="utf-8")
    (RESULTS / "rerank_top1_shift_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("OK:", rerank_md)


if __name__ == "__main__":
    main()
