from __future__ import annotations

from typing import Any

from .routing import interpolate_position


def _factor(
    category: str,
    label: str,
    detail: str,
    impact_minutes: int,
    severity: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "label": label,
        "detail": detail,
        "impact_minutes": impact_minutes,
        "severity": severity,
    }


def _build_delay_factors(route: dict[str, Any], live_signals: dict[str, Any]) -> list[dict[str, Any]]:
    weather = live_signals["weather"]
    traffic = live_signals["traffic"]
    factors: list[dict[str, Any]] = []

    if weather["severity"] == "HIGH":
        factors.append(_factor("weather", "Weather", weather["summary"], 18, "HIGH"))
    elif weather["severity"] == "MEDIUM":
        factors.append(_factor("weather", "Weather", weather["summary"], 8, "MEDIUM"))

    if traffic["severity"] == "HIGH":
        factors.append(_factor("traffic", "Traffic", traffic["summary"], 24, "HIGH"))
    elif traffic["severity"] == "MEDIUM":
        factors.append(_factor("traffic", "Traffic", traffic["summary"], 11, "MEDIUM"))

    load_tons = float(route.get("load_tons", 0))
    if load_tons >= 6:
        factors.append(_factor("load", "Load", f"{load_tons:.0f} ton payload reduces maneuver speed", 6, "MEDIUM"))

    cargo_type = route.get("cargo_type", "")
    telemetry_temp = route.get("telemetry_temperature_c")
    temp = float(telemetry_temp) if telemetry_temp is not None else 20.0
    if cargo_type in ["Pharmaceuticals", "Perishables"]:
        if temp > 8.0:
            factors.append(_factor("temperature", "Temperature", f"Cargo bay at {temp:.1f} C exceeds safe threshold", 45, "HIGH"))
        elif temp < 2.0:
            factors.append(_factor("temperature", "Temperature", f"Cargo bay at {temp:.1f} C is critically low", 40, "HIGH"))
        elif temp > 6.0:
            factors.append(_factor("temperature", "Temperature", f"Cargo bay at {temp:.1f} C is nearing the safe limit", 10, "MEDIUM"))

    distance_km = float(route.get("distance_km", 0))
    route_options = route.get("route_options", [])
    if distance_km >= 120 or len(route_options) <= 1:
        if len(route_options) <= 1:
            factors.append(_factor("bottleneck", "Bottleneck", "Limited alternate corridors available for this lane", 13, "HIGH"))
        else:
            factors.append(_factor("bottleneck", "Bottleneck", "Long-haul corridor compounds choke-point exposure", 9, "MEDIUM"))

    if route.get("status") == "REROUTED":
        factors.append(_factor("reroute", "Reroute transition", "Recently switched onto an alternate corridor", 7, "LOW"))
    elif route.get("status") == "WATCHLIST":
        factors.append(_factor("watchlist", "Watchlist", "This shipment is already under elevated observation", 5, "LOW"))

    return sorted(factors, key=lambda factor: factor["impact_minutes"], reverse=True)


def _recommend_action(route: dict[str, Any], predicted_delay_minutes: int) -> str:
    if route["risk_score"] >= 75 or predicted_delay_minutes >= 24:
        return "Recommended reroute: shift to the alternate corridor and alert the downstream hub."
    if route["risk_score"] >= 55:
        return "Recommended reroute: stage an alternate corridor and keep the shipment on watch."
    return "Recommended reroute: keep the current corridor active and continue monitoring."


def _prediction_severity(route: dict[str, Any], predicted_delay_minutes: int) -> str:
    if route["risk_score"] >= 75 or predicted_delay_minutes >= 24:
        return "HIGH"
    if route["risk_score"] >= 55 or predicted_delay_minutes >= 12:
        return "MEDIUM"
    return "LOW"


def _build_improvement_snapshot(route: dict[str, Any], predicted_delay_minutes: int) -> dict[str, Any]:
    route_options = route.get("route_options", [])
    current_option = route_options[0] if route_options else {}
    current_eta = int(current_option.get("duration_minutes", route.get("eta_minutes", 0)))

    comparison_option = None
    if route.get("status") == "REROUTED":
        comparison_option = next((option for option in route_options[1:] if option.get("label") == "Previous path"), None)
    if comparison_option is None:
        comparison_option = next((option for option in route_options[1:] if option.get("distance_km") is not None), None)

    before_base = int(comparison_option.get("duration_minutes", current_eta)) if comparison_option else current_eta
    after_base = current_eta
    before_projected = before_base + predicted_delay_minutes

    improvement_offset = 8 if route.get("status") == "REROUTED" and comparison_option else 0
    after_projected = max(after_base + predicted_delay_minutes - improvement_offset, after_base)
    improvement_minutes = max(before_projected - after_projected, 0)

    return {
        "before_eta_minutes": before_projected,
        "after_eta_minutes": after_projected,
        "improvement_minutes": improvement_minutes,
        "comparison_label": comparison_option.get("label", "Current path") if comparison_option else "Current path",
        "recommended_path_label": current_option.get("label", "Primary path"),
    }


def annotate_routes_with_predictions(
    routes: list[dict[str, Any]],
    live_signals: dict[str, Any],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for route in routes:
        updated_route = dict(route)
        progress_ratio = min(max(float(updated_route.get("progress_ratio", 0.2)), 0.05), 0.95)
        factors = _build_delay_factors(updated_route, live_signals)
        predicted_delay_minutes = sum(factor["impact_minutes"] for factor in factors[:3])
        projected_eta_minutes = int(updated_route.get("eta_minutes", 0)) + predicted_delay_minutes
        distance_km = float(updated_route.get("distance_km", 0))
        on_time_probability = max(18, min(97, round(100 - (updated_route["risk_score"] * 0.62) - (predicted_delay_minutes * 0.85))))
        prediction_severity = _prediction_severity(updated_route, predicted_delay_minutes)
        confidence_score = max(52, min(96, round(on_time_probability - (len(factors) * 2) + 9)))
        improvement_snapshot = _build_improvement_snapshot(updated_route, predicted_delay_minutes)

        updated_route["progress_percent"] = round(progress_ratio * 100)
        updated_route["distance_remaining_km"] = round(distance_km * (1 - progress_ratio), 1)
        updated_route["projected_eta_minutes"] = projected_eta_minutes
        updated_route["current_position"] = interpolate_position(updated_route.get("map_geometry"), progress_ratio) or updated_route["current_location"]
        updated_route["ai_prediction"] = {
            "predicted_delay_minutes": predicted_delay_minutes,
            "on_time_probability": on_time_probability,
            "confidence_score": confidence_score,
            "severity": prediction_severity,
            "recommended_action": _recommend_action(updated_route, predicted_delay_minutes),
            "recommended_reroute": improvement_snapshot["recommended_path_label"],
            "factors": factors[:5],
            "improvement": improvement_snapshot,
            "summary": (
                f"Dispatch intelligence predicts a {predicted_delay_minutes} minute delay window on {updated_route['route_id']} "
                f"with {confidence_score}% confidence and {prediction_severity.lower()} severity."
            ),
        }
        enriched.append(updated_route)

    return enriched
