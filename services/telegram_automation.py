"""Secure credentials and Windows startup-task management for Telegram reminders."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import keyring

from database.db import DatabaseManager


KEYRING_SERVICE = "StudyFlow.TelegramReminders"
SCHEDULER_TASK_NAME = "StudyFlow Telegram Reminders"
KEYRING_ACCOUNTS = {
    "telegram_bot_token": "telegram_bot_token",
    "telegram_chat_id": "telegram_chat_id",
    "groq_api_key": "groq_api_key",
}


def _require_os_credential_manager() -> None:
    try:
        backend = keyring.get_keyring()
        priority = backend.priority
    except Exception as exc:
        raise RuntimeError("The OS credential manager is not available.") from exc
    if priority <= 0:
        raise RuntimeError("No secure OS credential manager is available.")


def save_automation_credentials(bot_token: str, chat_id: str, api_key: str) -> None:
    """Store automation secrets in the active OS credential manager."""
    _require_os_credential_manager()
    credentials = {
        "telegram_bot_token": bot_token.strip(),
        "telegram_chat_id": chat_id.strip(),
        "groq_api_key": api_key.strip(),
    }
    for name, value in credentials.items():
        if value:
            keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNTS[name], value)


def get_automation_credentials() -> dict[str, str]:
    """Read automation secrets from the OS credential manager."""
    return {
        name: keyring.get_password(KEYRING_SERVICE, account) or ""
        for name, account in KEYRING_ACCOUNTS.items()
    }


def delete_automation_credentials() -> None:
    """Remove StudyFlow's Telegram automation secrets from the credential manager."""
    _require_os_credential_manager()
    for account in KEYRING_ACCOUNTS.values():
        if keyring.get_password(KEYRING_SERVICE, account) is not None:
            keyring.delete_password(KEYRING_SERVICE, account)


def enable_automatic_reminders(
    db: DatabaseManager,
    provider: str,
    model: str,
    ollama_url: str,
    bot_token: str,
    chat_id: str,
    api_key: str,
) -> None:
    """Save settings and secrets, then install and start the Windows scheduler."""
    if provider not in {"groq", "ollama"}:
        raise ValueError("Select Groq or Ollama as the AI provider.")
    if not model.strip():
        raise ValueError("Select an AI model.")
    if not bot_token.strip() or not chat_id.strip():
        raise ValueError("Enter the Telegram bot token and chat ID.")
    if provider == "groq" and not api_key.strip():
        raise ValueError("Enter the Groq API key.")
    if provider == "ollama":
        parsed_url = urlparse(ollama_url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("Enter a valid Ollama server URL, such as http://localhost:11434.")

    _require_windows_scheduler()
    save_automation_credentials(bot_token, chat_id, api_key)
    try:
        with db.transaction() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);",
                [
                    ("telegram_auto_enabled", "1"),
                    ("telegram_auto_provider", provider),
                    ("telegram_auto_model", model.strip()),
                    ("telegram_auto_ollama_url", ollama_url.strip()),
                ],
            )
        register_background_scheduler(db.db_path)
    except Exception:
        with db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('telegram_auto_enabled', '0');"
            )
        delete_automation_credentials()
        raise


def disable_automatic_reminders(db: DatabaseManager) -> None:
    """Disable future runs, remove the logon task, and delete stored credentials."""
    with db.transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('telegram_auto_enabled', '0');"
        )
    unregister_background_scheduler()
    delete_automation_credentials()


def _require_windows_scheduler() -> None:
    if os.name != "nt":
        raise RuntimeError("Closed-app Telegram reminders are currently supported on Windows only.")


def _run_schtasks(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    executable = shutil.which("schtasks.exe")
    if not executable:
        raise RuntimeError("Windows Task Scheduler (schtasks.exe) is not available.")
    try:
        result = subprocess.run(
            [executable, *arguments],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Could not manage the Windows startup task: {exc}") from exc
    if check and result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(details or "Windows Task Scheduler returned an error.")
    return result


def register_background_scheduler(db_path: str) -> None:
    """Register and start a hidden scheduler at the current user's next logon."""
    _require_windows_scheduler()

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    scheduler_script = Path(__file__).resolve().parent.parent / "telegram_scheduler.py"
    if not pythonw.is_file():
        raise RuntimeError(f"Could not find pythonw.exe next to the Python interpreter: {pythonw}")
    if not scheduler_script.is_file():
        raise RuntimeError(f"Background scheduler script was not found: {scheduler_script}")

    task_command = f'"{pythonw}" "{scheduler_script}" --db-path "{Path(db_path).resolve()}"'
    _run_schtasks([
        "/Create",
        "/TN", SCHEDULER_TASK_NAME,
        "/SC", "ONLOGON",
        "/TR", task_command,
        "/RL", "LIMITED",
        "/F",
    ])
    try:
        _run_schtasks(["/Run", "/TN", SCHEDULER_TASK_NAME])
    except RuntimeError:
        _run_schtasks(["/Delete", "/TN", SCHEDULER_TASK_NAME, "/F"], check=False)
        raise


def unregister_background_scheduler() -> None:
    """Disable the current scheduler process and remove the Windows logon task."""
    _require_windows_scheduler()
    _run_schtasks(["/End", "/TN", SCHEDULER_TASK_NAME], check=False)
    _run_schtasks(["/Delete", "/TN", SCHEDULER_TASK_NAME, "/F"])
