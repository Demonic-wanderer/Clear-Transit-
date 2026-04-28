from typing import Any

import requests

from .config import get_settings


def send_webhook(alert: dict[str, Any]) -> bool:
    webhook_url = get_settings().webhook_url
    if not webhook_url:
        return False

    try:
        payload = {
            "event": alert.get("event_type", "unknown_event"),
            "severity": alert.get("severity", "low"),
            "timestamp": alert.get("timestamp", ""),
        }

        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        print("Webhook Status:", response.status_code)
        return True
    except Exception as e:
        print(f"Failed to send webhook: {e}")
        return False
