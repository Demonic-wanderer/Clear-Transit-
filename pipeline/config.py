from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[1]
ROUTES_PATH = ROOT_DIR / "Data Architect" / "routes.json"
ALERTS_DB_PATH = ROOT_DIR / "Records" / "alerts.db"
ENV_PATH = ROOT_DIR / ".env"


def _load_dotenv() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _as_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError:
        return default


def _as_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    secret_key: str | None
    weather_api_key: str | None
    traffic_api_key: str | None
    weather_city: str
    traffic_lat: float
    traffic_lon: float
    routing_api_base: str
    webhook_url: str | None
    alert_cooldown_seconds: int


def get_settings() -> Settings:
    return Settings(
        secret_key=os.getenv("SECRET_KEY"),
        weather_api_key=os.getenv("WEATHER_API_KEY"),
        traffic_api_key=os.getenv("TRAFFIC_API_KEY") or os.getenv("TRAFFIC_API"),
        weather_city=os.getenv("WEATHER_CITY", "Indore"),
        traffic_lat=_as_float("TRAFFIC_LAT", 22.7196),
        traffic_lon=_as_float("TRAFFIC_LON", 75.8577),
        routing_api_base=os.getenv("ROUTING_API_BASE", "https://router.project-osrm.org"),
        webhook_url=os.getenv("WEBHOOK_URL"),
        alert_cooldown_seconds=max(_as_int("ALERT_COOLDOWN_SECONDS", 300), 0),
    )
