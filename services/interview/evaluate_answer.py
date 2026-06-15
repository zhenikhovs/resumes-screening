"""Оценка ответа кандидата через Groq (ChatGroq), как в ноутбуке."""
import json
import os
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config.interview_config import LLM_MODEL_NAME, LLM_TEMPERATURE
from services.interview.prompts import EVALUATION_SYSTEM_PROMPT, build_evaluation_user_message
from services.utils import save_json


def _parse_json_from_llm(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"В ответе LLM нет JSON: {content[:500]}")
    data = json.loads(text[start : end + 1])
    score = int(data.get("score", 0))
    data["score"] = max(0, min(10, score))
    if "feedback" not in data and "summary" in data:
        data["feedback"] = data["summary"]
    feedback = str(data.get("feedback", "")).strip()
    data["feedback"] = feedback
    return data


def evaluate_answer(
    vacancy_text: str,
    question: str,
    reference_answer: str,
    candidate_answer: str,
    groq_api_key: str | None = None,
) -> dict[str, Any]:
    """Возвращает {"score": int, "feedback": str}."""
    api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("Нет GROQ_API_KEY. Задайте переменную окружения или передайте groq_api_key.")

    llm = ChatGroq(
        temperature=LLM_TEMPERATURE,
        model_name=LLM_MODEL_NAME,
        groq_api_key=api_key,
    )
    user_message = build_evaluation_user_message(
        vacancy_text=vacancy_text,
        question=question,
        reference_answer=reference_answer,
        candidate_answer=candidate_answer,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", EVALUATION_SYSTEM_PROMPT),
            ("human", "{user_message}"),
        ]
    )
    chain = prompt | llm
    response = chain.invoke({"user_message": user_message})
    return _parse_json_from_llm(response.content)


def evaluate_and_save(
    vacancy_text: str,
    question: str,
    reference_answer: str,
    candidate_answer: str,
    output_path,
    question_id: str = "",
    groq_api_key: str | None = None,
) -> dict[str, Any]:
    result = evaluate_answer(
        vacancy_text=vacancy_text,
        question=question,
        reference_answer=reference_answer,
        candidate_answer=candidate_answer,
        groq_api_key=groq_api_key,
    )
    payload = {
        "question_id": question_id,
        "question": question,
        "score": result["score"],
        "feedback": result["feedback"],
        "model": LLM_MODEL_NAME,
    }
    save_json(output_path, payload)
    return payload
