import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

IATA = str

@dataclass(frozen=True)
class Airport:
    iata: IATA
    name: str
    city: str
    country: str
    lat: float
    lon: float

@dataclass(frozen=True)
class Carrier:
    iata: str
    name: str

@dataclass(frozen=True)
class Edge:
    dest: IATA
    km: float
    minutes: int
    price: float
    daily: int
    departures: Tuple[str, ...]
    carriers: Tuple[Carrier, ...]

@dataclass(frozen=True)
class GraphData:
    airports: Dict[IATA, Airport]
    graph: Dict[IATA, List[Edge]]
    edge_lookup: Dict[IATA, Dict[IATA, Edge]]

def _f(x, d=0.0):
    try: return float(x)
    except: return d

def _i(x, d=0):
    try: return int(x)
    except: return d

def load_graph(path: Path) -> GraphData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    airports, graph, lookup = {}, {}, {}

    for code, info in raw.items():
        airports[code] = Airport(
            iata=code,
            name=str(info.get("name", "")),
            city=str(info.get("city_name", "")),
            country=str(info.get("country", "")),
            lat=_f(info.get("latitude")),
            lon=_f(info.get("longitude")),
        )

    for src, info in raw.items():
        if src not in airports: 
            continue
        edges, row = [], {}
        for r in (info.get("routes") or []):
            dest = str(r.get("iata", "")).strip()
            if not dest or dest not in airports:
                continue
            carriers = []
            for c in (r.get("carriers") or []):
                cc = c or {}
                carriers.append(Carrier(iata=str(cc.get("iata", "")).strip(), name=str(cc.get("name", "")).strip()))
            e = Edge(
                dest=dest,
                km=_f(r.get("km", 0)),
                minutes=_i(r.get("min", 0)),
                price=_f(r.get("price_sgd", 0)),
                daily=_i(r.get("daily_flights", 0)),
                departures=tuple((r.get("departures_local") or [])[:12]),
                carriers=tuple(carriers),
            )
            edges.append(e)
            row[dest] = e
        graph[src] = edges
        lookup[src] = row

    for a in airports:
        graph.setdefault(a, [])
        lookup.setdefault(a, {})

    return GraphData(airports=airports, graph=graph, edge_lookup=lookup)

def all_carrier_codes(gd: GraphData) -> List[str]:
    s = set()
    for src in gd.edge_lookup:
        for e in gd.edge_lookup[src].values():
            for c in e.carriers:
                if c.iata:
                    s.add(c.iata)
    return sorted(s)