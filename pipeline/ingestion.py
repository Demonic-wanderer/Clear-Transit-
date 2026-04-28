from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from .config import get_settings


WEATHER_API = "https://api.openweathermap.org/data/2.5/weather"
TRAFFIC_API = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_weather() -> dict[str, Any]:
    settings = get_settings()

    if not settings.weather_api_key:
        return {
            "source": "weather",
            "timestamp": _iso_now(),
            "condition": "haze",
            "temp_c": 31,
            "city": settings.weather_city,
        }

    try:
        response = requests.get(
            WEATHER_API,
            params={"q": settings.weather_city, "appid": settings.weather_api_key, "units": "metric"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        return {
            "source": "weather",
            "timestamp": _iso_now(),
            "condition": data.get("weather", [{}])[0].get("description", "clear"),
            "temp_c": round(float(data.get("main", {}).get("temp", 30)), 1),
            "city": settings.weather_city,
        }
    except requests.RequestException:
        return {
            "source": "weather",
            "timestamp": _iso_now(),
            "condition": "moderate rain",
            "temp_c": 29,
            "city": settings.weather_city,
        }


def fetch_traffic() -> dict[str, Any]:
    settings = get_settings()

    if not settings.traffic_api_key:
        return {
            "source": "traffic",
            "timestamp": _iso_now(),
            "speed_kmph": 24,
            "free_flow_kmph": 52,
            "corridor": "Indore radial",
        }

    try:
        response = requests.get(
            TRAFFIC_API,
            params={
                "point": f"{settings.traffic_lat},{settings.traffic_lon}",
                "unit": "KMPH",
                "key": settings.traffic_api_key,
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json().get("flowSegmentData", {})

        return {
            "source": "traffic",
            "timestamp": _iso_now(),
            "speed_kmph": data.get("currentSpeed", 32),
            "free_flow_kmph": data.get("freeFlowSpeed", 50),
            "corridor": "Indore radial",
        }
    except requests.RequestException:
        return {
            "source": "traffic",
            "timestamp": _iso_now(),
            "speed_kmph": 18,
            "free_flow_kmph": 50,
            "corridor": "Indore radial",
        }
