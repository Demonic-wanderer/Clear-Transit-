from __future__ import annotations

from typing import Any


def normalize_weather(raw_data: dict[str, Any], location_id: str = "INDORE_CLUSTER") -> dict[str, Any]:
    condition = raw_data.get("condition", "clear").lower()
    temp_c = float(raw_data.get("temp_c", 30))

    if any(keyword in condition for keyword in ("storm", "cloudburst", "heavy rain")):
        severity = "HIGH"
    elif any(keyword in condition for keyword in ("rain", "fog", "haze")) or temp_c >= 38:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return {
        "event_type": "weather",
        "location": location_id,
        "severity": severity,
        "summary": f"{condition.title()} in {raw_data.get('city', 'the corridor')} at {temp_c:.0f} deg C",
        "timestamp": raw_data["timestamp"],
        "raw": raw_data,
    }


def normalize_traffic(raw_data: dict[str, Any], location_id: str = "INDORE_CLUSTER") -> dict[str, Any]:
    speed_kmph = float(raw_data.get("speed_kmph", 30))
    free_flow_kmph = max(float(raw_data.get("free_flow_kmph", 45)), 1.0)
    flow_ratio = speed_kmph / free_flow_kmph

    if flow_ratio < 0.45:
        severity = "HIGH"
    elif flow_ratio < 0.7:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return {
        "event_type": "traffic",
        "location": location_id,
        "severity": severity,
        "summary": (
            f"{raw_data.get('corridor', 'Network corridor')} moving at "
            f"{speed_kmph:.0f} km/h versus {free_flow_kmph:.0f} km/h free flow"
        ),
        "timestamp": raw_data["timestamp"],
        "raw": raw_data,
    }
