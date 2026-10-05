import json
import ssl

import httpx
import truststore

from .config import settings


class OpenRouterError(RuntimeError):
    pass


def _extract_content(response_json: dict) -> str:
    try:
        return response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def _extract_tokens(response_json: dict) -> int:
    try:
        return int(response_json.get("usage", {}).get("total_tokens", 0))
    except (TypeError, ValueError):
        return 0


async def call_openrouter(messages: list, response_format: dict | None = None) -> dict:
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
    }
    if response_format:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    verify = settings.OPENROUTER_CA_BUNDLE or truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    try:
        async with httpx.AsyncClient(timeout=60.0, verify=verify) as client:
            response = await client.post(
                settings.OPENROUTER_BASE_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise OpenRouterError(
            "Не удалось получить ответ от OpenRouter. "
            "Проверьте API-ключ, интернет-соединение и SSL-сертификат."
        ) from exc


async def get_bot_response(system_prompt: str, history: list, user_message: str) -> dict:
    first_message_note = (
        "\n\nТехнический статус диалога: это первое сообщение новой переписки. "
        "Не ссылайся на предыдущие обращения и начни диалог как новый."
        if not history
        else "\n\nТехнический статус диалога: это продолжение текущей переписки."
    )
    messages = [{"role": "system", "content": system_prompt + first_message_note}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response_json = await call_openrouter(messages)
    content = _extract_content(response_json)
    tokens = _extract_tokens(response_json)

    return {"content": content, "tokens": tokens}


async def extract_patient_info(dialog_text: str) -> dict:
    system_prompt = (
        "Ты — ассистент, который извлекает данные из диалога. "
        "Верни строго JSON-объект с ключами: name, phone, complaint. "
        "complaint — интересующая услуга, причина обращения или пожелание клиента. "
        "Учитывай только данные, явно сообщённые клиентом. Если клиент исправил имя "
        "или телефон, верни последнее явно указанное значение. "
        "Если поле не найдено, верни пустую строку."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": dialog_text},
    ]

    response_json = await call_openrouter(
        messages, response_format={"type": "json_object"}
    )
    content = _extract_content(response_json)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {}

    return {
        "name": str(data.get("name", "")).strip(),
        "phone": str(data.get("phone", "")).strip(),
        "complaint": str(data.get("complaint", "")).strip(),
    }