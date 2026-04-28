from __future__ import annotations

from typing import Any

import requests

from .config import get_settings


def interpolate_position(geometry: dict[str, Any] | None, progress_ratio: float) -> dict[str, float] | None:
    if not geometry or geometry.get("type") != "LineString":
        return None

    coordinates = geometry.get("coordinates", [])
    if len(coordinates) < 2:
        return None

    clamped_ratio = min(max(progress_ratio, 0.0), 1.0)
    segment_lengths: list[float] = []
    total_length = 0.0

    for index in range(len(coordinates) - 1):
        start = coordinates[index]
        end = coordinates[index + 1]
        dx = float(end[0]) - float(start[0])
        dy = float(end[1]) - float(start[1])
        length = (dx * dx + dy * dy) ** 0.5
        segment_lengths.append(length)
        total_length += length

    if total_length == 0:
        lon, lat = coordinates[0]
        return {"lat": lat, "lon": lon}

    target_length = total_length * clamped_ratio
    travelled = 0.0

    for index, length in enumerate(segment_lengths):
        if travelled + length >= target_length:
            start = coordinates[index]
            end = coordinates[index + 1]
            local_ratio = 0.0 if length == 0 else (target_length - travelled) / length
            lon = float(start[0]) + ((float(end[0]) - float(start[0])) * local_ratio)
            lat = float(start[1]) + ((float(end[1]) - float(start[1])) * local_ratio)
            return {"lat": lat, "lon": lon}
        travelled += length

    lon, lat = coordinates[-1]
    return {"lat": lat, "lon": lon}


def _coordinates_with_progress(
    geometry: dict[str, Any] | None,
    progress_ratio: float,
) -> tuple[list[list[float]], list[list[float]], list[float] | None]:
    if not geometry or geometry.get("type") != "LineString":
        return [], [], None

    coordinates = geometry.get("coordinates", [])
    if len(coordinates) < 2:
        return coordinates, [], coordinates[0] if coordinates else None

    clamped_ratio = min(max(progress_ratio, 0.0), 1.0)
    segment_lengths: list[float] = []
    total_length = 0.0

    for index in range(len(coordinates) - 1):
        start = coordinates[index]
        end = coordinates[index + 1]
        dx = float(end[0]) - float(start[0])
        dy = float(end[1]) - float(start[1])
        length = (dx * dx + dy * dy) ** 0.5
        segment_lengths.append(length)
        total_length += length

    if total_length == 0:
        pivot = coordinates[0]
        return [pivot], [pivot], pivot

    target_length = total_length * clamped_ratio
    travelled = 0.0
    completed: list[list[float]] = [list(coordinates[0])]

    for index, length in enumerate(segment_lengths):
        start = coordinates[index]
        end = coordinates[index + 1]
        if travelled + length >= target_length:
            local_ratio = 0.0 if length == 0 else (target_length - travelled) / length
            pivot = [
                float(start[0]) + ((float(end[0]) - float(start[0])) * local_ratio),
                float(start[1]) + ((float(end[1]) - float(start[1])) * local_ratio),
            ]
            if completed[-1] != pivot:
                completed.append(pivot)
            remaining = [pivot] + [list(coord) for coord in coordinates[index + 1 :]]
            return completed, remaining, pivot
        completed.append(list(end))
        travelled += length

    pivot = list(coordinates[-1])
    return completed, [pivot], pivot


def split_geometry_by_progress(
    geometry: dict[str, Any] | None,
    progress_ratio: float,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    completed, remaining, _ = _coordinates_with_progress(geometry, progress_ratio)
    completed_geometry = {"type": "LineString", "coordinates": completed} if len(completed) >= 2 else None
    remaining_geometry = {"type": "LineString", "coordinates": remaining} if len(remaining) >= 2 else None
    return completed_geometry, remaining_geometry


def get_route_bearing(geometry: dict[str, Any] | None, progress_ratio: float) -> float:
    if not geometry or geometry.get("type") != "LineString":
        return 0.0

    _, remaining, _ = _coordinates_with_progress(geometry, progress_ratio)
    if len(remaining) < 2:
        return 0.0

    start = remaining[0]
    end = remaining[min(1, len(remaining) - 1)]
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    if dx == 0 and dy == 0:
        return 0.0

    import math

    bearing = math.degrees(math.atan2(dx, dy))
    return (bearing + 360.0) % 360.0


def _format_instruction(step: dict[str, Any]) -> str:
    maneuver = step.get("maneuver", {})
    maneuver_type = maneuver.get("type", "continue")
    modifier = maneuver.get("modifier", "")
    name = step.get("name") or "the route ahead"

    if maneuver_type == "depart":
        return f"Depart onto {name}"
    if maneuver_type == "arrive":
        return "Arrive at destination"
    if maneuver_type == "roundabout":
        return f"Take the roundabout toward {name}"
    if maneuver_type == "turn" and modifier:
        return f"Turn {modifier} onto {name}"
    if maneuver_type == "merge":
        return f"Merge onto {name}"
    if maneuver_type == "on ramp":
        return f"Take the ramp onto {name}"
    if maneuver_type == "off ramp":
        return f"Take the exit toward {name}"
    return f"Continue on {name}"


def _extract_navigation_steps(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    cumulative_distance_km = 0.0

    for leg in candidate.get("legs", []):
        for step in leg.get("steps", []):
            distance_km = round(float(step.get("distance", 0.0)) / 1000, 1)
            duration_minutes = round(float(step.get("duration", 0.0)) / 60)
            cumulative_distance_km += distance_km
            steps.append(
                {
                    "instruction": _format_instruction(step),
                    "distance_km": distance_km,
                    "duration_minutes": duration_minutes,
                    "road_name": step.get("name") or "Unnamed road",
                    "cumulative_distance_km": round(cumulative_distance_km, 1),
                }
            )

    return steps


def _pick_next_step(navigation_steps: list[dict[str, Any]], distance_travelled_km: float) -> dict[str, Any] | None:
    for step in navigation_steps:
        if step["cumulative_distance_km"] > distance_travelled_km:
            return step
    return navigation_steps[-1] if navigation_steps else None


def _fallback_route_option(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "route_id": "fallback",
        "label": "Direct corridor",
        "summary": "Fallback geometry",
        "duration_minutes": route.get("eta_minutes", 0),
        "distance_km": route.get("distance_km", 0),
        "is_fastest": True,
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [route["current_location"]["lon"], route["current_location"]["lat"]],
                [route["destination_location"]["lon"], route["destination_location"]["lat"]],
            ],
        },
    }


def _select_primary_option(route: dict[str, Any], route_options: list[dict[str, Any]]) -> dict[str, Any]:
    if not route_options:
        return _fallback_route_option(route)

    # After a reroute, prefer a non-fastest alternative when available so the
    # dashboard visibly switches corridors instead of redrawing the same path.
    if route.get("status") == "REROUTED" and len(route_options) > 1:
        rerouted_option = dict(route_options[1])
        rerouted_option["label"] = "Rerouted path"
        rerouted_option["is_fastest"] = True

        remaining_options = [dict(option) for option in route_options[:1] + route_options[2:]]
        if remaining_options:
            remaining_options[0]["label"] = "Previous path"
            remaining_options[0]["is_fastest"] = False
        route_options[:] = [rerouted_option, *remaining_options]

    return route_options[0]


def get_route_options(route: dict[str, Any]) -> list[dict[str, Any]]:
    settings = get_settings()
    start = route["current_location"]
    end = route["destination_location"]
    coordinates = f"{start['lon']},{start['lat']};{end['lon']},{end['lat']}"
    url = f"{settings.routing_api_base.rstrip('/')}/route/v1/driving/{coordinates}"

    try:
        response = requests.get(
            url,
            params={
                "alternatives": "true",
                "overview": "full",
                "steps": "true",
                "geometries": "geojson",
            },
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("code") != "Ok":
            return [_fallback_route_option(route)]

        options: list[dict[str, Any]] = []
        for index, candidate in enumerate(payload.get("routes", [])[:3]):
            distance_km = round(float(candidate.get("distance", 0)) / 1000, 1)
            duration_minutes = round(float(candidate.get("duration", 0)) / 60)
            label = "Fastest" if index == 0 else f"Option {index + 1}"
            summary = f"{duration_minutes} min ETA - {distance_km} km"
            navigation_steps = _extract_navigation_steps(candidate)

            options.append(
                {
                    "route_id": f"{route['route_id']}-option-{index + 1}",
                    "label": label,
                    "summary": summary,
                    "duration_minutes": duration_minutes,
                    "distance_km": distance_km,
                    "is_fastest": index == 0,
                    "geometry": candidate.get("geometry", _fallback_route_option(route)["geometry"]),
                    "navigation_steps": navigation_steps[:8],
                }
            )

        return options or [_fallback_route_option(route)]
    except requests.RequestException:
        return [_fallback_route_option(route)]


def attach_route_options(routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched_routes: list[dict[str, Any]] = []

    for route in routes:
        updated_route = dict(route)
        route_options = get_route_options(updated_route)
        updated_route["route_options"] = route_options

        primary_option = _select_primary_option(updated_route, route_options)
        progress_ratio = float(updated_route.get("progress_ratio", 0.2))
        completed_geometry, remaining_geometry = split_geometry_by_progress(primary_option["geometry"], progress_ratio)
        distance_travelled_km = round(primary_option["distance_km"] * progress_ratio, 1)
        next_step = _pick_next_step(primary_option.get("navigation_steps", []), distance_travelled_km)
        updated_route["distance_km"] = primary_option["distance_km"]
        updated_route["eta_minutes"] = primary_option["duration_minutes"]
        updated_route["map_geometry"] = primary_option["geometry"]
        updated_route["route_quality"] = "road-following" if primary_option["route_id"] != "fallback" else "fallback"
        updated_route["current_position"] = interpolate_position(primary_option["geometry"], progress_ratio)
        updated_route["completed_geometry"] = completed_geometry
        updated_route["remaining_geometry"] = remaining_geometry
        updated_route["navigation_steps"] = primary_option.get("navigation_steps", [])
        updated_route["next_navigation_step"] = next_step
        updated_route["current_bearing"] = get_route_bearing(primary_option["geometry"], progress_ratio)

        enriched_routes.append(updated_route)

    return enriched_routes
