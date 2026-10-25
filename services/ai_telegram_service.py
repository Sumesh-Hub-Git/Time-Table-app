"""AI study-message generation and Telegram delivery."""

import json
from datetime import date
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from database.models import TaskInstance


GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MODEL_SUGGESTIONS = (
    DEFAULT_GROQ_MODEL,
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
)
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"
OLLAMA_MODEL_SUGGESTIONS = (
    DEFAULT_OLLAMA_MODEL,
    "llama3.1",
    "mistral",
    "gemma3",
    "qwen2.5",
)


def _post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    service_name: str = "service",
) -> dict:
    request_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "StudyFlow/1.0",
    }
    if headers:
        request_headers.update(headers)
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            details = exc.read().decode("utf-8", errors="replace")
        finally:
            exc.close()
        if exc.code == 403 and "1010" in details:
            raise RuntimeError(
                f"{service_name} blocked the request (HTTP 403, Cloudflare error 1010). "
                "This is a network or access-policy block, not an invalid-model error. "
                "Try the Ollama (Local) provider, or contact the provider's support if "
                "you need to use its cloud API."
            ) from exc
        raise RuntimeError(f"Request failed with HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not connect to the service: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("The service returned an invalid JSON response.") from exc

    if not isinstance(result, dict):
        raise RuntimeError("The service returned an unexpected response.")
    return result


def _get_json(url: str, headers: Optional[dict] = None, service_name: str = "service") -> dict:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "StudyFlow/1.0",
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers, method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            details = exc.read().decode("utf-8", errors="replace")
        finally:
            exc.close()
        if exc.code == 403 and "1010" in details:
            raise RuntimeError(
                f"{service_name} blocked the request (HTTP 403, Cloudflare error 1010). "
                "This is a network or access-policy block, not an invalid-model error. "
                "Try the Ollama (Local) provider, or contact the provider's support."
            ) from exc
        raise RuntimeError(f"Request failed with HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not connect to {service_name}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{service_name} returned an invalid JSON response.") from exc

    if not isinstance(result, dict):
        raise RuntimeError(f"{service_name} returned an unexpected response.")
    return result


def list_available_models(provider: str, api_key: str, ollama_url: str) -> list[str]:
    """Fetch available model IDs from Groq or locally installed Ollama models."""
    provider = provider.lower()
    if provider == "groq":
        if not api_key.strip():
            raise ValueError("Enter a Groq API key before refreshing available models.")
        response = _get_json(
            "https://api.groq.com/openai/v1/models",
            {"Authorization": "Bearer " + api_key.strip()},
            service_name="Groq",
        )
        models = [
            item["id"]
            for item in response.get("data", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
    elif provider == "ollama":
        parsed_url = urlparse(ollama_url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("Enter a valid Ollama server URL, such as http://localhost:11434.")
        response = _get_json(
            f"{ollama_url.strip().rstrip('/')}/api/tags",
            service_name="Ollama",
        )
        models = [
            item["name"]
            for item in response.get("models", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]
    else:
        raise ValueError("Select Groq or Ollama as the AI provider.")

    if not models:
        raise RuntimeError(f"No available models were returned by {provider.title()}.")
    return sorted(set(models), key=str.casefold)


def generate_study_message(
    provider: str,
    api_key: str,
    model: str,
    ollama_url: str,
    target_date: date,
    tasks: list[TaskInstance],
    user_name: str = "Student",
) -> str:
    """Generate a concise study update from the selected day's actual schedule."""
    provider = provider.lower()
    if provider not in {"groq", "ollama"}:
        raise ValueError("Select Groq or Ollama as the AI provider.")
    if not model.strip():
        raise ValueError("Enter a model name.")
    display_name = user_name.strip() or "Student"

    task_lines = [
        f"- {task.start_time}-{task.end_time}: {task.title} "
        f"({task.priority}; {'completed' if task.is_completed else 'pending'})"
        for task in tasks
    ]
    context = "\n".join(task_lines) if task_lines else "- No tasks are scheduled."
    prompt = (
        f"Create a concise, encouraging Telegram study update for {target_date.isoformat()} "
        f"addressing the user as {display_name!r}. Use their name naturally at least once. "
        "Use only the schedule below, mention progress accurately, and keep it under 100 words.\n"
        f"Tasks completed: {sum(task.is_completed for task in tasks)} of {len(tasks)}\n"
        f"Schedule:\n{context}"
    )
    messages = [
        {"role": "system", "content": "You are a helpful study-planning assistant."},
        {"role": "user", "content": prompt},
    ]

    if provider == "groq":
        if not api_key.strip():
            raise ValueError("Enter a Groq API key.")
        response = _post_json(
            GROQ_CHAT_URL,
            {"model": model.strip(), "messages": messages, "temperature": 0.7},
            {"Authorization": "Bearer " + api_key.strip()},
            service_name="Groq",
        )
        try:
            message = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Groq returned no generated message.") from exc
    else:
        parsed_url = urlparse(ollama_url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("Enter a valid Ollama server URL, such as http://localhost:11434.")
        response = _post_json(
            f"{ollama_url.strip().rstrip('/')}/api/chat",
            {"model": model.strip(), "messages": messages, "stream": False},
        )
        try:
            message = response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama returned no generated message.") from exc

    if not isinstance(message, str) or not message.strip():
        raise RuntimeError("The AI provider returned an empty message.")
    return message.strip()


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> None:
    """Send a user-approved message using the Telegram Bot API."""
    if not bot_token.strip() or not chat_id.strip():
        raise ValueError("Enter both a Telegram bot token and chat ID.")
    if not message.strip():
        raise ValueError("Generate or enter a message before sending.")

    response = _post_json(
        f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage",
        {"chat_id": chat_id.strip(), "text": message.strip()},
    )
    if response.get("ok") is not True:
        description = response.get("description", "Telegram rejected the message.")
        raise RuntimeError(str(description))
