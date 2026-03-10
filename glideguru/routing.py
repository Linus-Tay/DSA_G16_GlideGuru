from dataclasses import dataclass
from typing import Callable, List, Sequence, Tuple
import pandas as pd
from glideguru.data import Edge, GraphData, IATA
import heapq

@dataclass(frozen=True)
class RouteOption:
    id: int
    path: List[IATA]
    km: float
    minutes: int
    price: float
    hops: int
    score: float

def weight_fn(mode: str) -> Callable[[Edge], float]:
    if mode == "Shortest": return lambda e: e.km
    if mode == "Fastest": return lambda e: float(e.minutes)
    if mode == "Cheapest": return lambda e: e.price
    if mode == "Fewest hops": return lambda _e: 1.0
    if mode == "Cost-effective":
        return lambda e: (
        0.5 * e.price + 0.3 * e.minutes + 0.15 * 60 + 0.05 * e.km
    )
    return lambda e: e.price + 0.25 * float(e.minutes)

def totals(gd: GraphData, path: Sequence[IATA]) -> Tuple[float, int, float, int]:
    km = mins = 0
    price = 0.0
    for i in range(len(path) - 1):
        e = gd.edge_lookup[path[i]][path[i + 1]]
        km += e.km; mins += e.minutes; price += e.price
    return float(km), int(mins), float(price), len(path) - 1

def score_of(gd: GraphData, path: List[IATA], w: Callable[[Edge], float]) -> float:
    return sum(float(w(gd.edge_lookup[path[i]][path[i + 1]])) for i in range(len(path) - 1))

def legs_df(gd: GraphData, path: Sequence[IATA]) -> pd.DataFrame:
    rows = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        e = gd.edge_lookup[u][v]
        au, av = gd.airports[u], gd.airports[v]
        airlines = ", ".join([c.name for c in e.carriers if c.name]) or "Unknown"
        codes = ", ".join([c.iata for c in e.carriers if c.iata]) or "—"
        rows.append({
            "leg": i + 1,
            "from": f"{au.name} ({u})",
            "to": f"{av.name} ({v})",
            "km": round(e.km, 1),
            "min": int(e.minutes),
            "price": round(e.price, 2),
            "airlines": airlines,
            "codes": codes,
            "daily": int(e.daily),
            "departures": ", ".join(e.departures) if e.departures else "—",
        })
    return pd.DataFrame(rows)

def top_k_cost_effective(options: List[RouteOption], k: int) -> List[RouteOption]:

    if len(options) <= k:
        return sorted(options, key=lambda x: x.score)

    heap = []

    for opt in options:

        item = (-opt.score, opt)

        if len(heap) < k:
            heapq.heappush(heap, item)

        else:
            if opt.score < -heap[0][0]:
                heapq.heapreplace(heap, item)

    result = [item[1] for item in heap]

    return sorted(result, key=lambda x: x.score)