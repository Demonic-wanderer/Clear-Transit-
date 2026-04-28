from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from Records.models import Route, SessionLocal
from .relocation import relocate_route, save_routes


SEED_PATH = Path(__file__).resolve().parent.parent / "Data Architect" / "routes.json"

INDORE_HUBS: dict[str, dict[str, float]] = {
    "Indore Central Depot": {"lat": 22.7196, "lon": 75.8577},
    "M.R. 10 Medical Hub": {"lat": 22.7506, "lon": 75.8962},
    "Vijay Nagar Cold Chain Hub": {"lat": 22.7531, "lon": 75.8935},
    "Rau Industrial Point": {"lat": 22.6414, "lon": 75.8065},
    "Lasudia Freight Park": {"lat": 22.7429, "lon": 75.9036},
    "Scheme 78 Retail Cluster": {"lat": 22.7466, "lon": 75.8898},
    "Rajendra Nagar Warehouse": {"lat": 22.6701, "lon": 75.8267},
    "Bhawarkuan Commerce Strip": {"lat": 22.6924, "lon": 75.8676},
    "Dewas Naka Logistics Yard": {"lat": 22.7596, "lon": 75.8891},
    "Bombay Hospital District": {"lat": 22.7452, "lon": 75.9058},
    "Pithampur Connector Yard": {"lat": 22.6787, "lon": 75.7614},
    "Malwa Mill Textile Market": {"lat": 22.7134, "lon": 75.8736},
    "Super Corridor Fulfillment Hub": {"lat": 22.7987, "lon": 75.8815},
    "Palasia Dispatch Point": {"lat": 22.7265, "lon": 75.8823},
    "Navlakha Transit Hub": {"lat": 22.7004, "lon": 75.8754},
    "Geeta Bhawan Clinic Belt": {"lat": 22.7191, "lon": 75.8839},
    "Bengali Square Stockpoint": {"lat": 22.7058, "lon": 75.9114},
    "Airport Cargo Link": {"lat": 22.7278, "lon": 75.8011},
}

ALLOWED_STATUSES = {"STABLE", "MONITORING", "WATCHLIST", "REROUTED"}


def load_seed_shipments() -> list[dict[str, Any]]:
    if not SEED_PATH.exists():
        return []

    with SEED_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def list_shipments() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        routes = session.query(Route).order_by(Route.route_id.asc()).all()
        return [route.to_dict() for route in routes]


def _as_float(payload: dict[str, Any], field: str, *, minimum: float | None = None) -> float:
    raw = payload.get(field)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{field.replace('_', ' ').title()} must be a number") from None

    if minimum is not None and value < minimum:
        raise ValueError(f"{field.replace('_', ' ').title()} must be at least {minimum}")
    return round(value, 1)


def _as_int(payload: dict[str, Any], field: str, *, minimum: int | None = None) -> int:
    raw = payload.get(field)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{field.replace('_', ' ').title()} must be a whole number") from None

    if minimum is not None and value < minimum:
        raise ValueError(f"{field.replace('_', ' ').title()} must be at least {minimum}")
    return value


def _clean_text(payload: dict[str, Any], field: str) -> str:
    value = str(payload.get(field, "")).strip()
    if not value:
        raise ValueError(f"{field.replace('_', ' ').title()} is required")
    return value


def _next_numeric_id(prefix: str, values: list[str], start: int) -> str:
    highest = start - 1
    for value in values:
        if not value.startswith(prefix):
            continue
        suffix = value.removeprefix(prefix)
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}{highest + 1:03d}"


def _validate_status(status: str) -> str:
    normalized = status.strip().upper()
    if normalized not in ALLOWED_STATUSES:
        raise ValueError("Status must be Stable, Monitoring, Watchlist, or Rerouted")
    return normalized


def _distance_from_eta(eta_minutes: int) -> int:
    return max(4, round(eta_minutes * 0.48))


def _lookup_location(name: str) -> dict[str, float]:
    location = INDORE_HUBS.get(name)
    if location is None:
        raise ValueError(f"Unknown Indore hub: {name}")
    return location


def shipment_options() -> dict[str, Any]:
    return {
        "hubs": sorted(INDORE_HUBS.keys()),
        "statuses": sorted(ALLOWED_STATUSES),
    }


def create_shipment(payload: dict[str, Any]) -> dict[str, Any]:
    shipments = list_shipments()
    route_id = _next_numeric_id("R", [route["route_id"] for route in shipments], 1)
    shipment_id = _next_numeric_id("SHP-", [route["shipment_id"] for route in shipments], 100)
    source = _clean_text(payload, "source")
    destination = _clean_text(payload, "destination")
    if source == destination:
        raise ValueError("Source and destination must be different")

    route = {
        "route_id": route_id,
        "shipment_id": shipment_id,
        "vehicle_label": _clean_text(payload, "vehicle_label"),
        "cargo_type": _clean_text(payload, "cargo_type"),
        "cargo_value_usd": _as_int(payload, "cargo_value_usd", minimum=1),
        "telemetry_temperature_c": _as_float(payload, "telemetry_temperature_c", minimum=-30),
        "telemetry_status": "NORMAL",
        "source": source,
        "destination": destination,
        "distance_km": _distance_from_eta(_as_int(payload, "eta_minutes", minimum=1)),
        "eta_minutes": _as_int(payload, "eta_minutes", minimum=1),
        "load_tons": _as_float(payload, "load_tons", minimum=0),
        "status": _validate_status(_clean_text(payload, "status")),
        "progress_ratio": round(min(max(float(payload.get("progress_ratio", 0.18)), 0), 0.95), 2),
        "base_risk_score": _as_int(payload, "base_risk_score", minimum=0),
        "risk_score": _as_int(payload, "base_risk_score", minimum=0),
        "current_location": _lookup_location(source),
        "destination_location": _lookup_location(destination),
        "last_action": "Shipment added from shipment database",
    }

    shipments.append(route)
    save_routes(shipments)
    return route


def update_shipment(route_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    shipments = list_shipments()
    route = next((item for item in shipments if item["route_id"] == route_id), None)
    if route is None:
        raise ValueError("Shipment not found")

    source = _clean_text(payload, "source")
    destination = _clean_text(payload, "destination")
    if source == destination:
        raise ValueError("Source and destination must be different")

    route.update(
        {
            "vehicle_label": _clean_text(payload, "vehicle_label"),
            "cargo_type": _clean_text(payload, "cargo_type"),
            "cargo_value_usd": _as_int(payload, "cargo_value_usd", minimum=1),
            "telemetry_temperature_c": _as_float(payload, "telemetry_temperature_c", minimum=-30),
            "source": source,
            "destination": destination,
            "eta_minutes": _as_int(payload, "eta_minutes", minimum=1),
            "load_tons": _as_float(payload, "load_tons", minimum=0),
            "status": _validate_status(_clean_text(payload, "status")),
            "base_risk_score": _as_int(payload, "base_risk_score", minimum=0),
            "risk_score": _as_int(payload, "base_risk_score", minimum=0),
            "distance_km": _distance_from_eta(_as_int(payload, "eta_minutes", minimum=1)),
            "current_location": _lookup_location(source),
            "destination_location": _lookup_location(destination),
            "last_action": "Shipment updated in shipment database",
        }
    )
    save_routes(shipments)
    return route


def reset_seed_shipments() -> list[dict[str, Any]]:
    seed_shipments = deepcopy(load_seed_shipments())
    save_routes(seed_shipments, prune_missing=True)
    return seed_shipments


def reroute_shipment(route_id: str, reason: str) -> dict[str, Any]:
    return relocate_route(route_id, reason)
