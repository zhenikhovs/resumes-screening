"""Понятные сообщения об ошибках для HR (без путей и технических деталей)."""
import re


def to_user_message(exc: BaseException) -> str:
    raw = str(exc).strip()
    low = raw.lower()

    if "не найдено резюме" in low or "не найдено резюме на hh" in low:
        return (
            "По этой фразе на hh.ru не нашлось резюме. "
            "Попробуйте другие слова: должность, навыки (например: «php разработчик»)."
        )

    if "токен headhunter" in low or "переавторизуйтесь" in low or "token" in low and "hh" in low:
        return (
            "Нужно обновить доступ к hh.ru. "
            "Попросите администратора выполнить вход в HeadHunter для приложения."
        )

    if "403" in raw and "ваканс" in low:
        return (
            "Не удалось открыть вакансию на hh.ru. "
            "Проверьте ссылку и что вакансия ваша (под тем же аккаунтом, что подключён к системе)."
        )

    if "404" in raw and "ваканс" in low:
        return "Вакансия не найдена на hh.ru. Возможно, она снята с публикации — проверьте ссылку."

    if "429" in raw or "лимит api" in low:
        return "Слишком много запросов к hh.ru. Подождите 10–15 минут и запустите подбор снова."

    if "resumes_camp_" in raw or "нет файла резюме" in low or "resume_file" in low:
        return (
            "Резюме с hh.ru не сохранились полностью. "
            "Запустите новый подбор — если ошибка повторится, сообщите администратору."
        )

    if "resume_download_failed" in low or "скачано 0" in low:
        return (
            "Не удалось загрузить полные резюме с hh.ru. "
            "Проверьте доступ к hh.ru и попробуйте другую поисковую фразу."
        )

    if "не удалось извлечь id" in low:
        return "Неверная ссылка на вакансию. Скопируйте адрес со страницы вакансии на hh.ru."

    if "user-agent" in low or "bad_user_agent" in low:
        return "Ошибка настройки доступа к hh.ru. Сообщите администратору системы."

    if "нет демо-данных" in low:
        return (
            "Нет подключения к hh.ru и нет демонстрационных данных. "
            "Настройте доступ к HeadHunter или обратитесь к администратору."
        )

    # Убираем длинные пути из текста, если всё же просочились
    cleaned = re.sub(r"/[\w./-]+\.(json|log)", "…", raw)
    if len(cleaned) > 220:
        cleaned = cleaned[:220] + "…"

    if cleaned and cleaned != raw and not _looks_technical(cleaned):
        return cleaned

    return (
        "Подбор не завершился из‑за технической ошибки. "
        "Запустите новый подбор. Если ситуация повторится — сообщите администратору."
    )


def _looks_technical(text: str) -> bool:
    markers = ("traceback", "import ", "http://", "https://api", "runtimeerror:", "file not found")
    low = text.lower()
    return any(m in low for m in markers)
