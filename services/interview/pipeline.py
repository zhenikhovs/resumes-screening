"""Сквозной пайплайн видео-интервью: аудио → ASR → оценка → итог по интервью."""
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from config.interview_config import INTERVIEW_AVG_DECIMALS, INTERVIEW_PASS_THRESHOLD
from config.paths import INTERVIEWS_RESULTS_DIR
from services.interview.evaluate_answer import evaluate_and_save
from services.interview.extract_audio import prepare_audio
from services.interview.scenarios import (
    get_question_by_id,
    interview_dir,
    load_interview_meta,
    load_scenario,
    question_dir,
    resolve_vacancy_text,
    save_interview_meta,
)
from services.interview.transcribe import transcribe_audio
from services.utils import load_json, save_json

load_dotenv()


def init_interview(
    interview_id: str,
    candidate_id: str,
    query: str,
) -> dict[str, Any]:
    scenario = load_scenario(query)
    meta = {
        "interview_id": interview_id,
        "candidate_id": candidate_id,
        "query": query,
        "pass_threshold": INTERVIEW_PASS_THRESHOLD,
        "question_ids": [q["question_id"] for q in scenario["questions"]],
    }
    save_interview_meta(interview_id, meta)
    print(f"[+] Интервью {interview_id}: query={query}, вопросов={len(meta['question_ids'])}")
    return meta


def process_question(
    interview_id: str,
    question_id: str,
    video_path: Path,
    *,
    skip_extract: bool = False,
    skip_transcribe: bool = False,
    skip_evaluate: bool = False,
) -> dict[str, Any]:
    """
    Один вопрос: видео/аудио → WAV → transcript → evaluation.
    """
    meta = load_interview_meta(interview_id)
    query = meta["query"]
    scenario = load_scenario(query)
    q = get_question_by_id(scenario, question_id)

    qdir = question_dir(interview_id, question_id)
    qdir.mkdir(parents=True, exist_ok=True)

    raw_dest = qdir / f"raw{video_path.suffix.lower() or '.mp4'}"
    if video_path.resolve() != raw_dest.resolve():
        shutil.copy2(video_path, raw_dest)

    audio_path = qdir / "audio_16k.wav"
    transcript_path = qdir / "transcript.json"
    evaluation_path = qdir / "evaluation.json"

    if not skip_extract:
        prepare_audio(raw_dest, audio_path)
        print(f"[+] Аудио: {audio_path}")

    if not skip_transcribe:
        if not audio_path.exists():
            prepare_audio(raw_dest, audio_path)
        transcribe_audio(audio_path, transcript_path)
        print(f"[+] Транскрипт: {transcript_path}")

    if skip_evaluate:
        return {
            "interview_id": interview_id,
            "question_id": question_id,
            "transcript_path": str(transcript_path),
            "evaluation_path": None,
        }

    transcript = load_json(transcript_path)
    candidate_answer = (transcript.get("text") or "").strip()
    if not candidate_answer:
        raise ValueError(f"Пустой транскрипт для {question_id}. Проверьте аудио/видео.")

    if not skip_evaluate:
        vacancy_text = resolve_vacancy_text(scenario)
        evaluate_and_save(
            vacancy_text=vacancy_text,
            question=q["question"],
            reference_answer=q["reference_answer"],
            candidate_answer=candidate_answer,
            output_path=evaluation_path,
            question_id=question_id,
        )
        print(f"[+] Оценка: {evaluation_path}")

    return {
        "interview_id": interview_id,
        "question_id": question_id,
        "transcript_path": str(transcript_path),
        "evaluation_path": str(evaluation_path),
    }


def finalize_interview(interview_id: str) -> dict[str, Any]:
    """Средний балл по всем вопросам сценария; approved если avg >= порога."""
    meta = load_interview_meta(interview_id)
    query = meta["query"]
    scenario = load_scenario(query)
    threshold = float(meta.get("pass_threshold", INTERVIEW_PASS_THRESHOLD))

    questions_out = []
    scores = []

    for q in scenario["questions"]:
        qid = q["question_id"]
        eval_path = question_dir(interview_id, qid) / "evaluation.json"
        if not eval_path.exists():
            print(f"[!] Нет оценки для {qid}, пропуск в среднем (запустите process)")
            continue
        ev = load_json(eval_path)
        score = int(ev.get("score", 0))
        scores.append(score)
        transcript_path = question_dir(interview_id, qid) / "transcript.json"
        transcript_text = ""
        if transcript_path.exists():
            tr = load_json(transcript_path)
            transcript_text = (tr.get("text") or "").strip()
        questions_out.append(
            {
                "question_id": qid,
                "question": q.get("question", ""),
                "score": score,
                "feedback": ev.get("feedback") or ev.get("summary", ""),
                "transcript": transcript_text,
            }
        )

    if not scores:
        raise ValueError(f"Нет ни одной оценки для interview_id={interview_id}")

    avg = round(sum(scores) / len(scores), INTERVIEW_AVG_DECIMALS)
    approved = avg >= threshold

    summary = {
        "interview_id": interview_id,
        "candidate_id": meta.get("candidate_id"),
        "query": query,
        "pass_threshold": threshold,
        "questions": questions_out,
        "questions_evaluated": len(scores),
        "questions_total": len(scenario["questions"]),
        "interview_score_avg": avg,
        "approved": approved,
    }

    out_interview = interview_dir(interview_id) / "interview_summary.json"
    save_json(out_interview, summary)

    INTERVIEWS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_results = INTERVIEWS_RESULTS_DIR / f"{interview_id}_{query}.json"
    save_json(out_results, summary)

    status = "ОДОБРЕН" if approved else "НЕ ОДОБРЕН"
    print(f"[+] {interview_id}: средний балл={avg}, порог={threshold} → {status}")
    print(f"[+] Сводка: {out_interview}")
    return summary
