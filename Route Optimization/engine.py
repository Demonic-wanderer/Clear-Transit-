import requests
from typing import Any

from pipeline.config import get_settings

def calculate_optimal_reroute(routes: list[dict[str, Any]], route_id: str, reason: str) -> dict[str, Any]:
    for route in routes:
        if route["route_id"] != route_id:
            continue

        base_risk = int(route.get("base_risk_score", route.get("risk_score", 50)))
        route["status"] = "REROUTED"
        route["risk_score"] = min(max(int(route.get("risk_score", 50)), base_risk + 15), 100)
        route["last_action"] = f"Optimized Reroute due to: {reason}"
        
        start = route.get("current_location", {"lat": route.get("current_lat"), "lon": route.get("current_lon")})
        end =   route.get("destination_location", {"lat": route.get("dest_lat"), "lon": route.get("dest_lon")})
        
        lon1 = start.get("lon") or route.get("current_lon")
        lat1 = start.get("lat") or route.get("current_lat")
        lon2 = end.get("lon") or route.get("dest_lon")
        lat2 = end.get("lat") or route.get("dest_lat")

        if lat1 and lon1 and lat2 and lon2:
            routing_api_base = get_settings().routing_api_base.rstrip("/")
            url = f"{routing_api_base}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?alternatives=true&overview=full"
            try:
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                payload = resp.json()
                routes_osrm = payload.get("routes", [])
                
                if len(routes_osrm) > 1:
                    chosen = routes_osrm[1]
                elif len(routes_osrm) == 1:
                    chosen = routes_osrm[0]
                else:
                    chosen = None
                    
                if chosen:
                    route["distance_km"] = round(float(chosen.get("distance", 0)) / 1000, 1)
                    route["eta_minutes"] = round(float(chosen.get("duration", 0)) / 60)
            except Exception as e:
                print(f"OSRM rerouting failed: {e}")
                route["eta_minutes"] = max(int(route.get("eta_minutes", 90)) - 15, 20)
        else:
            route["eta_minutes"] = max(int(route.get("eta_minutes", 90)) - 15, 20)

        return route

    raise ValueError(f"Unknown route_id: {route_id}")
