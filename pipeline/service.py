from __future__ import annotations

from statistics import mean
from typing import Any

from .db_logger import fetch_recent_alerts, init_db, log_to_db
from .dispatcher import send_webhook
from .ingestion import fetch_traffic, fetch_weather
from .normalizer import normalize_traffic, normalize_weather
from .prediction import annotate_routes_with_predictions
from .relocation import load_routes, reroute_highest_risk_route, save_routes
from .routing import attach_route_options


import json
from pathlib import Path


def _load_seed_routes() -> list[dict[str, Any]]:
    seed_path = Path(__file__).resolve().parent.parent / "Data Architect" / "routes.json"
    if not seed_path.exists():
        return []

    with seed_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _backfill_route_metadata(routes: list[dict[str, Any]], seed_routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seed_by_id = {route["route_id"]: route for route in seed_routes}
    hydrated_routes: list[dict[str, Any]] = []

    for route in routes:
        updated = dict(route)
        seed = seed_by_id.get(route.get("route_id"))
        if seed:
            for field in (
                "shipment_id",
                "vehicle_label",
                "source",
                "destination",
                "distance_km",
                "eta_minutes",
                "load_tons",
                "cargo_type",
                "cargo_value_usd",
                "telemetry_temperature_c",
                "telemetry_status",
            ):
                updated[field] = seed.get(field)

            for field in ("progress_ratio", "base_risk_score"):
                if updated.get(field) is None:
                    updated[field] = seed.get(field)

            updated["current_location"] = seed.get("current_location")
            updated["destination_location"] = seed.get("destination_location")

        hydrated_routes.append(updated)

    return hydrated_routes


def _merge_seed_routes(routes: list[dict[str, Any]], seed_routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not seed_routes:
        return routes

    seed_by_id = {route["route_id"]: route for route in seed_routes}
    merged = _backfill_route_metadata(routes, seed_routes)
    existing_ids = {route.get("route_id") for route in merged}

    for seed in seed_routes:
        if seed["route_id"] not in existing_ids:
            merged.append(dict(seed))

    return merged

def ensure_bootstrap() -> None:
    init_db()
    routes = load_routes()
    seed_routes = _load_seed_routes()

    if routes:
        hydrated_routes = _merge_seed_routes(routes, seed_routes)
        if hydrated_routes != routes:
            save_routes(hydrated_routes)
        return

    if seed_routes:
        save_routes(seed_routes)
    else:
        save_routes([])


def _severity_rank(severity: str) -> int:
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(severity, 0)


def _enrich_routes(routes: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    highest_severity = max((_severity_rank(event["severity"]) for event in events), default=0)
    enriched: list[dict[str, Any]] = []

    for route in routes:
        updated_route = dict(route)
        base_risk = int(updated_route.get("base_risk_score", updated_route.get("risk_score", 0)))
        status_bonus = 10 if updated_route.get("status") == "REROUTED" else 6 if updated_route.get("status") == "WATCHLIST" else 0
        
        import random
        cargo_value = float(updated_route.get("cargo_value_usd", 0))
        value_multiplier = 1.5 if cargo_value > 200000 else 1.2 if cargo_value > 30000 else 1.0
        
        current_temp = float(updated_route.get("telemetry_temperature_c", 20.0))
        updated_route["telemetry_temperature_c"] = round(current_temp + random.uniform(-0.8, 0.8), 1)

        risk_score = min(int((base_risk + (highest_severity * 8) + status_bonus) * value_multiplier), 100)
        updated_route["risk_score"] = risk_score
        enriched.append(updated_route)

    if enriched:
        save_routes(enriched)

    return enriched


def _build_kpis(routes: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    total_shipments = len(routes)
    rerouted = sum(1 for route in routes if route.get("status") == "REROUTED")
    at_risk = sum(1 for route in routes if int(route.get("risk_score", 0)) >= 55)
    avg_eta = round(mean([int(route.get("eta_minutes", 0)) for route in routes]), 1) if routes else 0
    network_risk = round(mean([int(route.get("risk_score", 0)) for route in routes]), 1) if routes else 0
    sms_notifications = sum(1 for a in alerts if a.get("severity") == "HIGH")

    return {
        "total_shipments": total_shipments,
        "rerouted_shipments": rerouted,
        "at_risk_shipments": at_risk,
        "average_eta_minutes": avg_eta,
        "network_risk_score": network_risk,
        "recent_alert_count": len(alerts),
        "co2_saved_kg": rerouted * 105,
        "sms_dispatched": sms_notifications,
    }


def build_dashboard_snapshot() -> dict[str, Any]:
    routes = attach_route_options(load_routes())
    alerts = fetch_recent_alerts()
    weather = fetch_weather()
    traffic = fetch_traffic()
    weather_event = normalize_weather(weather)
    traffic_event = normalize_traffic(traffic)
    live_signals = {
        "weather": weather_event,
        "traffic": traffic_event,
    }
    routes = annotate_routes_with_predictions(routes, live_signals)

    return {
        "mission": {
            "title": "[Smart Supply Chains] Resilient Logistics and Dynamic Supply Chain Optimization",
            "objective": (
                "Continuously analyze transit conditions, surface disruptions early, "
                "and trigger or recommend route adjustments before delays cascade."
            ),
        },
        "live_signals": live_signals,
        "kpis": _build_kpis(routes, alerts),
        "routes": routes,
        "alerts": alerts,
    }


def run_monitoring_cycle(apply_relocation: bool = False) -> dict[str, Any]:
    weather = fetch_weather()
    traffic = fetch_traffic()
    events = [normalize_weather(weather), normalize_traffic(traffic)]

    mock_notifications = []
    for event in events:
        was_logged = log_to_db(event)
        if was_logged and event.get("severity") == "HIGH":
            notification_sent = send_webhook(event)
            status = "sent" if notification_sent else "staged in demo mode"
            mock_notifications.append(
                f"Stakeholder notification {status}: alert near {event.get('location')} ({event.get('event_type')})"
            )

    routes = _enrich_routes(load_routes(), events)
    route_action = None

    if apply_relocation and any(event["severity"] == "HIGH" for event in events):
        route_action = reroute_highest_risk_route("detected disruption")
        routes = load_routes()

    routes = attach_route_options(routes)
    alerts = fetch_recent_alerts()
    live_signals = {
        "weather": events[0],
        "traffic": events[1],
    }
    routes = annotate_routes_with_predictions(routes, live_signals)

    return {
        "mission": {
            "title": "[Smart Supply Chains] Resilient Logistics and Dynamic Supply Chain Optimization",
            "objective": (
                "Continuously analyze transit conditions, surface disruptions early, "
                "and trigger or recommend route adjustments before delays cascade."
            ),
        },
        "live_signals": live_signals,
        "kpis": _build_kpis(routes, alerts),
        "routes": routes,
        "alerts": alerts,
        "last_action": route_action,
        "mock_notifications": mock_notifications,
    }
