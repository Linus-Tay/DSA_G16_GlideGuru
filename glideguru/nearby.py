from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Set

from glideguru.data import Edge, GraphData, IATA


_EARTH_RADIUS_KM = 6371.0


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = (math.radians(x) for x in (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    a = min(1.0, max(0.0, a))
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _allows(edge: Edge, allowed: Optional[Set[str]]) -> bool:
    if not allowed:
        return True
    return any(c.iata in allowed for c in edge.carriers)


def build_route_payload(gd: GraphData, path: Sequence[IATA], option_id: int = 1) -> Optional[Dict[str, Any]]:
    """
    Build a route payload in the same shape used by the frontend
    without re-running any core search algorithm.
    """
    if not path or len(path) < 2:
        return None

    total_km = 0.0
    total_minutes = 0
    total_price = 0.0
    legs: List[Dict[str, Any]] = []

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]

        edge = gd.edge_lookup.get(u, {}).get(v)
        if edge is None:
            return None

        au = gd.airports.get(u)
        av = gd.airports.get(v)
        if au is None or av is None:
            return None

        total_km += float(edge.km)
        total_minutes += int(edge.minutes)
        total_price += float(edge.price)

        legs.append({
            "from_code": u,
            "to_code": v,
            "from_name": au.name,
            "from_city": au.city,
            "from_country": au.country,
            "to_name": av.name,
            "to_city": av.city,
            "to_country": av.country,
            "km": float(edge.km),
            "minutes": int(edge.minutes),
            "price": float(edge.price),
            "daily": int(edge.daily),
            "departures": list(edge.departures),
            "airlines": [
                {"code": c.iata, "name": c.name}
                for c in edge.carriers
            ],
        })

    return {
        "id": int(option_id),
        "path": list(path),
        "km": float(total_km),
        "minutes": int(total_minutes),
        "price": float(total_price),
        "hops": len(path) - 1,
        "score": 0.0,
        "legs": legs,
    }


def get_nearby_viable_swaps(
    gd: GraphData,
    path: Sequence[IATA],
    clicked_index: int,
    blocked: Optional[Set[IATA]] = None,
    allowed: Optional[Set[str]] = None,
    radius_km: float = 120.0,
    limit: int = 8,
    option_id: int = 1,
) -> List[Dict[str, Any]]:
    """
    Find nearby airports that can replace exactly one airport in an
    already-found route while preserving adjacent legs.

    Example:
    A -> B -> C
    Replacing B with X is allowed only if:
    - A -> X exists
    - X -> C exists
    """
    blocked = blocked or set()

    if not path or len(path) < 2:
        return []

    if clicked_index < 0 or clicked_index >= len(path):
        return []

    original_option = build_route_payload(gd, path, option_id=option_id)
    if original_option is None:
        return []

    clicked_code = path[clicked_index]
    clicked_airport = gd.airports.get(clicked_code)
    if clicked_airport is None:
        return []

    prev_code = path[clicked_index - 1] if clicked_index > 0 else None
    next_code = path[clicked_index + 1] if clicked_index < len(path) - 1 else None

    results: List[Dict[str, Any]] = []

    for code, airport in gd.airports.items():
        if code == clicked_code:
            continue
        if code in blocked:
            continue
        if code in path:
            continue

        dist = _haversine(clicked_airport.lat, clicked_airport.lon, airport.lat, airport.lon)
        if dist > radius_km:
            continue

        if prev_code is not None:
            in_edge = gd.edge_lookup.get(prev_code, {}).get(code)
            if in_edge is None or not _allows(in_edge, allowed):
                continue

        if next_code is not None:
            out_edge = gd.edge_lookup.get(code, {}).get(next_code)
            if out_edge is None or not _allows(out_edge, allowed):
                continue

        new_path = list(path)
        new_path[clicked_index] = code

        option = build_route_payload(gd, new_path, option_id=option_id)
        if option is None:
            continue

        results.append({
            "iata": code,
            "name": airport.name,
            "city": airport.city,
            "country": airport.country,
            "distance_from_clicked_km": round(dist, 1),
            "delta_km": round(float(option["km"]) - float(original_option["km"]), 1),
            "delta_minutes": int(option["minutes"]) - int(original_option["minutes"]),
            "delta_price": round(float(option["price"]) - float(original_option["price"]), 2),
            "option": option,
        })

    results.sort(
        key=lambda x: (
            abs(float(x["delta_minutes"])),
            abs(float(x["delta_price"])),
            abs(float(x["delta_km"])),
            float(x["distance_from_clicked_km"]),
        )
    )

    return results[:limit]