from flask import Flask, render_template, request, jsonify, Response
import glideguru.config as config
from glideguru.data import load_graph, all_carrier_codes
from glideguru.algorithms import bfs_hops, yen_k_paths, astar, bidirectional_dijkstra
from glideguru.routing import totals, weight_fn, score_of, top_k_cost_effective, RouteOption
from glideguru.unionfind import UnionFind
import time
import csv
import io
import json

start_time = time.time()


def build_connectivity(gd):
    uf = UnionFind(gd.graph.keys())
    for u in gd.graph:
        for e in gd.graph[u]:
            uf.union(u, e.dest)
    return uf


app = Flask(__name__)

GD = load_graph(config.DATA_PATH)
UF = build_connectivity(GD)
AIRPORTS = GD.airports
CARRIER_CODES = all_carrier_codes(GD)


def airport_label(code: str) -> str:
    a = AIRPORTS[code]
    return f"{code} — {a.city}, {a.country}"


def legs_list(path: list[str]) -> list[dict]:
    legs: list[dict] = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        e = GD.edge_lookup[u][v]
        au, av = AIRPORTS[u], AIRPORTS[v]

        airlines = [{"code": c.iata, "name": c.name} for c in e.carriers if c.iata or c.name]
        legs.append(
            {
                "leg": i + 1,
                "from_code": u,
                "from_name": au.name,
                "from_city": au.city,
                "from_country": au.country,
                "to_code": v,
                "to_name": av.name,
                "to_city": av.city,
                "to_country": av.country,
                "km": round(float(e.km), 1),
                "minutes": int(e.minutes),
                "price": round(float(e.price), 2),
                "daily": int(e.daily),
                "departures": list(e.departures) if e.departures else [],
                "airlines": airlines,
            }
        )
    return legs


def search_paths(start: str, goal: str, mode: str, blocked: set[str], allowed, max_hops: int, want: int):
    """
    Centralized search wrapper so /api/search, /print, and export endpoints use
    the same logic.

    Fewest hops:
    - primary route comes from BFS
    - extra options come from Yen with unit edge weights so alternatives are also
      hop-oriented rather than cost-oriented

    Weighted modes:
    - primary route comes from Bidirectional Dijkstra
    - extra options come from Yen's algorithm for distinct alternatives
    """
    if mode == "Fewest hops":
        paths: list[list[str]] = []
        primary = bfs_hops(GD, start, goal, blocked, allowed, max_hops=max_hops)
        if primary:
            paths.append(primary)

        for candidate in yen_k_paths(
            GD,
            start,
            goal,
            weight_fn("Fewest hops"),
            k=want,
            blocked=blocked,
            allowed=allowed,
            max_hops=max_hops,
        ):
            if candidate not in paths:
                paths.append(candidate)
        return paths

    wf = weight_fn(mode)
    paths: list[list[str]] = []
    primary, _ = bidirectional_dijkstra(GD, start, goal, wf, blocked, allowed, max_hops)
    if primary:
        paths.append(primary)

    use_astar = (mode == "Shortest")
    for candidate in yen_k_paths(
        GD,
        start,
        goal,
        wf,
        k=max(want, 1),
        blocked=blocked,
        allowed=allowed,
        max_hops=max_hops,
        use_astar=use_astar,
    ):
        if candidate not in paths:
            paths.append(candidate)
    return paths


@app.get("/")
def index():
    airports = [
    {
        "code": c,
        "label": airport_label(c),
        "name": AIRPORTS[c].name,
        "city": AIRPORTS[c].city,
        "country": AIRPORTS[c].country,
        "lat": AIRPORTS[c].lat,
        "lon": AIRPORTS[c].lon,
    }
    for c in sorted(AIRPORTS)
]
    return render_template(
        "index.html",
        app_name=config.APP_NAME,
        tagline=config.TAGLINE,
        airports=airports,
        carrier_codes=CARRIER_CODES,
        defaults={"max_hops": config.DEFAULT_MAX_HOPS, "limit": 6},
    )


@app.post("/api/search")
def api_search():
    body = request.get_json(force=True)

    start = body.get("start")
    goal = body.get("goal")
    mode = body.get("mode", "Shortest")
    max_hops = int(body.get("max_hops", config.DEFAULT_MAX_HOPS))
    limit = int(body.get("limit", 6))

    blocked = set(body.get("blocked", []))
    allowed_list = body.get("allowed", [])
    allowed = set(allowed_list) if allowed_list else None

    if start not in AIRPORTS or goal not in AIRPORTS:
        return jsonify({"error": "Invalid airport"}), 400

    if UF.find(start) != UF.find(goal):
        return jsonify({"options": [], "has_more": False})

    blocked.discard(start)
    blocked.discard(goal)

    want = max(1, min(limit + 1, 60))
    wf = weight_fn("Fewest hops") if mode == "Fewest hops" else weight_fn(mode)
    all_paths = search_paths(start, goal, mode, blocked, allowed, max_hops, want)
    has_more = len(all_paths) > limit
    paths = all_paths[:limit]

    options = []
    for i, p in enumerate(paths, 1):
        km, mins, price, hops = totals(GD, p)
        score = score_of(GD, p, wf)
        options.append(RouteOption(id=i, path=p, km=km, minutes=mins, price=price, hops=hops, score=score))

    if mode == "Cost-effective":
        options = top_k_cost_effective(options, limit)

    return jsonify(
        {
            "options": [
                {
                    "id": o.id,
                    "path": o.path,
                    "km": o.km,
                    "minutes": o.minutes,
                    "price": o.price,
                    "hops": o.hops,
                    "score": o.score,
                    "legs": legs_list(o.path),
                }
                for o in options
            ],
            "has_more": has_more,
        }
    )


def route_payload(path: list[str], option_id: int, start: str, goal: str, mode: str) -> dict:
    km, mins, price, hops = totals(GD, path)
    return {
        "id": option_id,
        "title": f"{config.APP_NAME}: {start} → {goal} (Option {option_id})",
        "path": path,
        "path_display": " → ".join(path),
        "mode": mode,
        "summary": {
            "km": km,
            "minutes": mins,
            "price": price,
            "connections": hops,
        },
        "legs": legs_list(path),
    }


def resolve_route_from_request():
    option_id = max(1, int(request.args.get("id", "1")))
    start = request.args.get("start")
    goal = request.args.get("goal")
    mode = request.args.get("mode", "Shortest")
    max_hops = int(request.args.get("max_hops", config.DEFAULT_MAX_HOPS))
    limit = int(request.args.get("limit", 6))
    blocked = set(request.args.get("blocked", "").split(",")) if request.args.get("blocked") else set()
    allowed = set(request.args.get("allowed", "").split(",")) if request.args.get("allowed") else None

    if not start or not goal or start not in AIRPORTS or goal not in AIRPORTS:
        return None

    if UF.find(start) != UF.find(goal):
        return None

    blocked.discard(start)
    blocked.discard(goal)

    want = max(1, min(limit, 60))
    paths = search_paths(start, goal, mode, blocked, allowed, max_hops, want)
    if not paths:
        return None

    idx = max(1, min(option_id, len(paths))) - 1
    return route_payload(paths[idx], idx + 1, start, goal, mode)


@app.get("/export/json")
def export_json():
    payload = resolve_route_from_request()
    if payload is None:
        return jsonify({"error": "No route available for export"}), 404

    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=itinerary_{payload['path'][0]}_{payload['path'][-1]}_option_{payload['id']}.json"}
    )


@app.get("/export/csv")
def export_csv():
    payload = resolve_route_from_request()
    if payload is None:
        return jsonify({"error": "No route available for export"}), 404

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Route", payload["path_display"]])
    writer.writerow(["Mode", payload["mode"]])
    writer.writerow(["Total Distance (km)", f"{payload['summary']['km']:.1f}"])
    writer.writerow(["Total Time (minutes)", payload["summary"]["minutes"]])
    writer.writerow(["Total Price (SGD)", f"{payload['summary']['price']:.2f}"])
    writer.writerow(["Connections", payload["summary"]["connections"]])
    writer.writerow([])
    writer.writerow([
        "Leg", "From Code", "From Airport", "From City", "From Country",
        "To Code", "To Airport", "To City", "To Country", "Distance (km)",
        "Duration (min)", "Price (SGD)", "Flights/day", "Airline Codes",
        "Airline Names", "Departures",
    ])
    for leg in payload["legs"]:
        writer.writerow([
            leg["leg"], leg["from_code"], leg["from_name"], leg["from_city"], leg["from_country"],
            leg["to_code"], leg["to_name"], leg["to_city"], leg["to_country"], f"{leg['km']:.1f}",
            leg["minutes"], f"{leg['price']:.2f}", leg["daily"],
            ", ".join([a["code"] for a in leg["airlines"] if a.get("code")]) or "—",
            ", ".join([a["name"] for a in leg["airlines"] if a.get("name")]) or "Unknown",
            ", ".join(leg["departures"]) if leg["departures"] else "—",
        ])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=itinerary_{payload['path'][0]}_{payload['path'][-1]}_option_{payload['id']}.csv"}
    )


@app.get("/print")
def print_view():
    payload = resolve_route_from_request()
    if payload is None:
        return render_template(
            "print.html",
            title=f"{config.APP_NAME}: No route",
            path="No route",
            km=0,
            mins=0,
            price=0,
            hops=0,
            table=[],
        )

    table = []
    for leg in payload["legs"]:
        airline_names = ", ".join([a["name"] for a in leg["airlines"] if a.get("name")]) or "Unknown"
        airline_codes = ", ".join([a["code"] for a in leg["airlines"] if a.get("code")]) or "—"
        table.append(
            {
                "leg": leg["leg"],
                "from": f'{leg["from_name"]} ({leg["from_code"]})',
                "to": f'{leg["to_name"]} ({leg["to_code"]})',
                "km": leg["km"],
                "min": leg["minutes"],
                "price": leg["price"],
                "airlines": airline_names,
                "codes": airline_codes,
                "daily": leg["daily"],
                "departures": ", ".join(leg["departures"]) if leg["departures"] else "—",
            }
        )

    return render_template(
        "print.html",
        title=payload["title"],
        path=payload["path_display"],
        km=payload["summary"]["km"],
        mins=payload["summary"]["minutes"],
        price=payload["summary"]["price"],
        hops=payload["summary"]["connections"],
        table=table,
    )


if __name__ == "__main__":
    app.run(debug=True)