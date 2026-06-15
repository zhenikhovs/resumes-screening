#!/usr/bin/env python3
"""
CLI пайплайна: предобработка и ранжирование.

Использование (из корня проекта):
  python run.py pre_clean    # pre-clean резюме и вакансий
  python run.py clean        # pre-cleaned → classical + transformer (только этот шаг при смене clean_*.py)
  python run.py rebuild      # pre_clean + clean (всё подготовленное с нуля от сырых JSON)
  python run.py rank         # ранжирование (все методы или --method bm25)
  python run.py pipeline     # clean + rank (данные уже должны быть собраны и pre-cleaned)
  python run.py pipeline_ranking [--classical] [--transformer]  # новый pipeline (фильтр по опыту + similarity + threshold + top-10)
  python run.py interview init|process|finalize  # этап 2: видео-интервью (см. docs/INTERVIEW_PIPELINE.md)

Для сбора данных: main.py (резюме), vacancies.py (вакансии).
"""
import argparse
import sys


def cmd_pre_clean(_):
    from services.preprocessing.pre_clean_resumes import process_files as process_resumes
    from services.preprocessing.pre_clean_vacancies import process_files as process_vacancies
    print("Pre-clean резюме...")
    process_resumes()
    print("Pre-clean вакансий...")
    process_vacancies()


def cmd_clean(_):
    from services.preprocessing.clean_resumes import process_files as process_resumes
    from services.preprocessing.clean_vacancies import main as process_vacancies
    print("Clean резюме → classical + transformer...")
    process_resumes()
    print("Clean вакансий → classical + transformer...")
    process_vacancies()


def cmd_rebuild(_):
    """Сырые данные → pre-cleaned → cleaned (classical + transformer) для резюме и вакансий."""
    cmd_pre_clean(_)
    cmd_clean(_)


def cmd_rank(args):
    method = (args.method or "").strip().lower()
    if method == "bm25":
        from services.ranking.bm25 import run_bm25
        run_bm25()
    elif method == "tfidf":
        from services.ranking.tfidf import run_tfidf
        run_tfidf()
    elif method == "e5":
        from services.ranking.e5 import run_e5
        run_e5()
    elif method == "minilm":
        from services.ranking.minilm import run_minilm
        run_minilm()
    elif method == "ru_sbert":
        from services.ranking.ru_sbert import run_rusbert
        run_rusbert()
    elif method == "mpnet":
        from services.ranking.mpnet import run_mpnet
        run_mpnet()
    elif not method or method == "all":
        from services.ranking.bm25 import run_bm25
        from services.ranking.tfidf import run_tfidf
        run_bm25()
        run_tfidf()
        print("Остальные ранкеры (e5, minilm, ru_sbert, mpnet) запускайте отдельно: python run.py rank --method e5")
    else:
        print(f"Неизвестный метод: {method}. Доступны: bm25, tfidf, e5, minilm, ru_sbert, mpnet, all")
        sys.exit(1)


def cmd_pipeline(args):
    cmd_clean(args)
    cmd_rank(args)


def cmd_pipeline_ranking(args):
    """Новый pipeline: фильтр по опыту (>=0.8*vacancy_exp), similarity, final_score, min-max, 90% порог, top-10."""
    run_classical = args.classical or (not args.classical and not args.transformer)
    run_transformer = args.transformer or (not args.classical and not args.transformer)
    if run_classical:
        from services.ranking.pipeline_classical import run_pipeline_classical
        run_pipeline_classical("bm25")
        run_pipeline_classical("tfidf")
    if run_transformer:
        from services.ranking.pipeline_transformer import run_pipeline_transformer
        run_pipeline_transformer(method=args.transformer_method or "e5")


def cmd_pipeline_rerank(args):
    """Второй этап: reranking cross-encoder поверх результатов transformer-pipeline.
    --model multilingual без --transformer-method: прогон для всех retrieval-методов (e5, minilm, ru_sbert, mpnet).
    --transformer-method e5: один метод; с --model all (по умолчанию) — прогон для всех трёх CE (russian, minilm, multilingual).
    """
    from services.ranking.cross_encoder_rerank import (
        run_cross_encoder_rerank,
        CROSS_ENCODER_MODELS,
    )
    from config.paths import PIPELINE_TRANSFORMER_RESULTS

    batch_size = args.batch_size
    model_name = args.model_name
    transformer_method = args.transformer_method
    model_key = args.model

    retrieval_methods = ("e5", "minilm", "ru_sbert", "mpnet")
    ce_keys = tuple(CROSS_ENCODER_MODELS)

    if transformer_method == "all" and model_key == "all":
        methods_to_run = [m for m in retrieval_methods if (PIPELINE_TRANSFORMER_RESULTS / m).exists()]
        for method in methods_to_run:
            for key in ce_keys:
                run_cross_encoder_rerank(method=method, model_name=None, model_key=key, batch_size=batch_size)
        return
    if transformer_method == "all":
        methods_to_run = [m for m in retrieval_methods if (PIPELINE_TRANSFORMER_RESULTS / m).exists()]
        for method in methods_to_run:
            run_cross_encoder_rerank(method=method, model_name=model_name, model_key=model_key, batch_size=batch_size)
        return
    if model_key == "all":
        for key in ce_keys:
            run_cross_encoder_rerank(method=transformer_method, model_name=None, model_key=key, batch_size=batch_size)
        return
    run_cross_encoder_rerank(
        method=transformer_method,
        model_name=model_name,
        model_key=model_key,
        batch_size=batch_size,
    )


def cmd_pipeline_rerank_classical(args):
    """Второй этап для classical: cross-encoder reranking поверх classical-pipeline (BM25 / TF-IDF)."""
    from services.ranking.cross_encoder_rerank_classical import run_cross_encoder_rerank_classical, CROSS_ENCODER_MODELS  # type: ignore[import]

    batch_size = args.batch_size
    model_name = args.model_name
    method = args.method
    model_key = args.model

    ce_keys = tuple(CROSS_ENCODER_MODELS)

    if method == "all" and model_key == "all":
        for m in ("bm25", "tfidf"):
            for key in ce_keys:
                run_cross_encoder_rerank_classical(method=m, model_name=None, model_key=key, batch_size=batch_size)
        return
    if method == "all":
        for m in ("bm25", "tfidf"):
            run_cross_encoder_rerank_classical(method=m, model_name=model_name, model_key=model_key, batch_size=batch_size)
        return
    if model_key == "all":
        for key in ce_keys:
            run_cross_encoder_rerank_classical(method=method, model_name=None, model_key=key, batch_size=batch_size)
        return

    run_cross_encoder_rerank_classical(
        method=method,
        model_name=model_name,
        model_key=model_key,
        batch_size=batch_size,
    )


def cmd_interview_init(args):
    from services.interview.pipeline import init_interview

    init_interview(args.interview_id, args.candidate_id, args.query)


def cmd_interview_process(args):
    from pathlib import Path

    from services.interview.pipeline import process_question

    process_question(
        args.interview_id,
        args.question_id,
        Path(args.video),
        skip_extract=args.skip_extract,
        skip_transcribe=args.skip_transcribe,
        skip_evaluate=args.skip_evaluate,
    )


def cmd_interview_finalize(args):
    from services.interview.pipeline import finalize_interview

    finalize_interview(args.interview_id)


def main():
    parser = argparse.ArgumentParser(description="Пайплайн: предобработка и ранжирование")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("pre_clean", help="Pre-clean: сырые резюме/вакансии → pre-cleaned")
    sub.add_parser("clean", help="Clean: pre-cleaned → classical + transformer (резюме и вакансии)")
    sub.add_parser("rebuild", help="Полная пересборка: pre_clean + clean")
    r = sub.add_parser("rank", help="Ранжирование (--method bm25|tfidf|e5|...|all)")
    r.add_argument("--method", default="all", help="bm25, tfidf, e5, minilm, ru_sbert, mpnet или all")
    sub.add_parser("pipeline", help="Выполнить clean + rank")
    pr = sub.add_parser("pipeline_ranking", help="Новый pipeline: фильтр по опыту + similarity + threshold + top-10")
    pr.add_argument("--classical", action="store_true", help="Только classical (BM25 similarity)")
    pr.add_argument("--transformer", action="store_true", help="Только transformer (эмбеддинги)")
    pr.add_argument("--transformer-method", default="e5", choices=("e5", "minilm", "ru_sbert", "mpnet"), help="Модель для transformer: e5, minilm, ru_sbert, mpnet")
    pr2 = sub.add_parser("pipeline_rerank", help="Второй этап: cross-encoder reranking поверх transformer-pipeline")
    pr2.add_argument("--transformer-method", default="all", choices=("e5", "minilm", "ru_sbert", "mpnet", "all"), help="Один метод или all — тогда прогон по всем CE моделям для этого метода")
    pr2.add_argument("--model", default="all", choices=("russian", "minilm", "multilingual", "all"), help="CE: russian, minilm, multilingual; all — прогон по всем retrieval-методам с этой CE")
    pr2.add_argument("--model-name", default=None, help="Полное имя cross-encoder модели (если задано, перекрывает --model)")
    pr2.add_argument("--batch-size", type=int, default=32, help="Размер батча для cross-encoder (32 или 64)")

    pr3 = sub.add_parser("pipeline_rerank_classical", help="Второй этап для classical: cross-encoder reranking поверх classical-pipeline (BM25 / TF-IDF)")
    pr3.add_argument("--method", default="all", choices=("bm25", "tfidf", "all"), help="Классический метод: bm25, tfidf или all для обоих")
    pr3.add_argument("--model", default="all", choices=("russian", "minilm", "multilingual", "all"), help="CE: russian, minilm, multilingual; all — прогон по всем CE моделям")
    pr3.add_argument("--model-name", default=None, help="Полное имя cross-encoder модели (если задано, перекрывает --model)")
    pr3.add_argument("--batch-size", type=int, default=32, help="Размер батча для cross-encoder (32 или 64)")

    iv = sub.add_parser("interview", help="Этап 2: видео-интервью (ASR + оценка Groq)")
    iv_sub = iv.add_subparsers(dest="interview_command", required=True)

    iv_init = iv_sub.add_parser("init", help="Создать интервью (meta.json)")
    iv_init.add_argument("--interview-id", required=True)
    iv_init.add_argument("--candidate-id", required=True)
    iv_init.add_argument("--query", required=True, help="Имя сценария, напр. backend_developer")

    iv_proc = iv_sub.add_parser("process", help="Обработать одно видео-ответ на вопрос")
    iv_proc.add_argument("--interview-id", required=True)
    iv_proc.add_argument("--question-id", required=True)
    iv_proc.add_argument("--video", required=True, help="Путь к видео или аудио")
    iv_proc.add_argument("--skip-extract", action="store_true")
    iv_proc.add_argument("--skip-transcribe", action="store_true")
    iv_proc.add_argument("--skip-evaluate", action="store_true")

    iv_fin = iv_sub.add_parser("finalize", help="Средний балл и approved по всем вопросам")
    iv_fin.add_argument("--interview-id", required=True)

    args = parser.parse_args()
    if args.command == "pre_clean":
        cmd_pre_clean(args)
    elif args.command == "clean":
        cmd_clean(args)
    elif args.command == "rebuild":
        cmd_rebuild(args)
    elif args.command == "rank":
        cmd_rank(args)
    elif args.command == "pipeline":
        cmd_pipeline(args)
    elif args.command == "pipeline_ranking":
        cmd_pipeline_ranking(args)
    elif args.command == "pipeline_rerank":
        cmd_pipeline_rerank(args)
    elif args.command == "pipeline_rerank_classical":
        cmd_pipeline_rerank_classical(args)
    elif args.command == "interview":
        if args.interview_command == "init":
            cmd_interview_init(args)
        elif args.interview_command == "process":
            cmd_interview_process(args)
        elif args.interview_command == "finalize":
            cmd_interview_finalize(args)


if __name__ == "__main__":
    main()
