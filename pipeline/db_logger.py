from __future__ import annotations

import sys
import os
from datetime import datetime
from typing import Any

# Ensure Records is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Records.models import SessionLocal, DisruptionEvent, init_db as models_init_db
from .config import get_settings

def init_db() -> None:
    models_init_db()


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def log_to_db(alert: dict[str, Any]) -> bool:
    cooldown_seconds = get_settings().alert_cooldown_seconds
    incoming_timestamp = _parse_timestamp(alert.get("timestamp"))

    with SessionLocal() as session:
        if cooldown_seconds > 0:
            latest_similar = (
                session.query(DisruptionEvent)
                .filter_by(
                    event_type=alert["event_type"],
                    severity=alert["severity"],
                    location=alert["location"],
                )
                .order_by(DisruptionEvent.id.desc())
                .first()
            )
            if latest_similar is not None:
                latest_timestamp = _parse_timestamp(latest_similar.timestamp)
                if incoming_timestamp is not None and latest_timestamp is not None:
                    if abs((incoming_timestamp - latest_timestamp).total_seconds()) < cooldown_seconds:
                        return False

        new_event = DisruptionEvent(
            event_type=alert["event_type"],
            severity=alert["severity"],
            location=alert["location"],
            summary=alert["summary"],
            timestamp=alert["timestamp"],
        )
        session.add(new_event)
        session.commit()
        return True

def fetch_recent_alerts(limit: int = 6) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        events = session.query(DisruptionEvent).order_by(DisruptionEvent.id.desc()).limit(limit).all()
        return [event.to_dict() for event in events]
