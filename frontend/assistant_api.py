"""Helpers for talking to the Flask Greenhouse Assistant's Ask capability."""
import requests

from api_client import BACKEND_URL, auth_headers

CHAT_TIMEOUT_SECONDS = 300  # 5 minute timeout; as allocated for Rocky


def ask(message, history):
    response = requests.post(
        f"{BACKEND_URL}/api/v1/assistant/chat",
        json={"message": message, "history": history},
        headers=auth_headers(),
        timeout=CHAT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json().get("answer")
