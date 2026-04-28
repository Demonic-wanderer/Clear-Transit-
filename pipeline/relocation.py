from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any

# Ensure Records is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from engine import calculate_optimal_reroute
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("engine", "Route Optimization/engine.py")
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    calculate_optimal_reroute = engine.calculate_optimal_reroute

from Records.models import SessionLocal, Route

def load_routes() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        routes = session.query(Route).all()
        return [route.to_dict() for route in routes]

def save_routes(routes: list[dict[str, Any]], prune_missing: bool = False) -> None:
    # Synchronizes the list of route dictionaries back to DB
    with SessionLocal() as session:
        incoming_ids = {route_dict["route_id"] for route_dict in routes}
        if prune_missing:
            if incoming_ids:
                session.query(Route).filter(~Route.route_id.in_(incoming_ids)).delete(synchronize_session=False)
            else:
                session.query(Route).delete(synchronize_session=False)

        for route_dict in routes:
            route_id = route_dict["route_id"]
            route = session.query(Route).filter_by(route_id=route_id).first()
            if not route:
                route = Route(route_id=route_id)
                session.add(route)
            
            route.shipment_id = route_dict.get("shipment_id")
            route.vehicle_label = route_dict.get("vehicle_label")
            route.source = route_dict.get("source")
            route.destination = route_dict.get("destination")
            route.distance_km = route_dict.get("distance_km")
            route.eta_minutes = route_dict.get("eta_minutes")
            route.load_tons = route_dict.get("load_tons")
            route.status = route_dict.get("status")
            route.progress_ratio = route_dict.get("progress_ratio")
            route.base_risk_score = route_dict.get("base_risk_score")
            route.risk_score = route_dict.get("risk_score")
            route.cargo_type = route_dict.get("cargo_type")
            route.cargo_value_usd = route_dict.get("cargo_value_usd")
            route.telemetry_temperature_c = route_dict.get("telemetry_temperature_c")
            route.telemetry_status = route_dict.get("telemetry_status")
            
            if "current_location" in route_dict:
                route.current_lat = route_dict["current_location"].get("lat")
                route.current_lon = route_dict["current_location"].get("lon")
            if "destination_location" in route_dict:
                route.dest_lat = route_dict["destination_location"].get("lat")
                route.dest_lon = route_dict["destination_location"].get("lon")
                
            route.last_action = route_dict.get("last_action")
        session.commit()

def relocate_route(route_id: str, reason: str) -> dict[str, Any]:
    routes = load_routes()
    route = calculate_optimal_reroute(routes, route_id, reason)
    save_routes(routes)
    return route

def reroute_highest_risk_route(reason: str) -> dict[str, Any] | None:
    routes = load_routes()
    if not routes:
        return None

    candidate = max(routes, key=lambda route: int(route.get("risk_score", 0)))
    return relocate_route(candidate["route_id"], reason)
