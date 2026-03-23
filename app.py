from flask import Flask, render_template, request, jsonify
import glideguru.config as config
from glideguru.data import load_graph, all_carrier_codes
from glideguru.algorithms import bfs_hops, yen_k_paths, astar
from glideguru.routing import totals, weight_fn, score_of, top_k_cost_effective, RouteOption
from glideguru.unionfind import UnionFind
import time

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
    Centralized search wrapper so /api/search and /print use the same logic.

    Fewest Connections:
    - use BFS to get the minimum-hop route first
    - use Yen to get additional hop-based alternatives
    - keep all routes up to max_hops
    - sort by hops first, then time, then price, then distance

    Other modes:
    - use Yen's K-shortest paths with the relevant weight function
    """
    if mode in {"Fewest Connections", "Fewest hops"}:
        paths: list[list[str]] = []

        # Find the best minimum-hop route within the user's upper-bound slider
        primary = bfs_hops(
            GD,
            start,
            goal,
            blocked,
            allowed,
            max_hops=max_hops
        )

        if not primary:
            return []

        paths.append(primary)

        # Find additional hop-based alternatives, still respecting max_hops
        alt_paths = yen_k_paths(
            GD,
            start,
            goal,
            weight_fn("Fewest Connections"),
            k=want,
            blocked=blocked,
            allowed=allowed,
            max_hops=max_hops,
            use_astar=False,
        )

        for candidate in alt_paths:
            hops = len(candidate) - 1
            if candidate not in paths and hops <= max_hops:
                paths.append(candidate)
        # Sort so the fewest-hop routes appear first.
        # Among equal-hop routes, prefer lower time, then lower price, then shorter distance.
        paths.sort(
            key=lambda p: (
                totals(GD, p)[3],  # hops
                totals(GD, p)[1],  # minutes
                totals(GD, p)[2],  # price
                totals(GD, p)[0],  # km
            )
        )

        return paths

    # For now, keep A* disabled because your Dijkstra is hop-aware
    # but A* is not yet hop-aware.
    use_astar = False

    return yen_k_paths(
        GD,
        start,
        goal,
        weight_fn(mode),
        k=want,
        blocked=blocked,
        allowed=allowed,
        max_hops=max_hops,
        use_astar=use_astar,
    )


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
    wf = weight_fn(mode)

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


@app.get("/print")
def print_view():
    option_id = request.args.get("id", "1")
    start = request.args.get("start")
    goal = request.args.get("goal")
    mode = request.args.get("mode", "Shortest")
    max_hops = int(request.args.get("max_hops", config.DEFAULT_MAX_HOPS))
    limit = int(request.args.get("limit", 6))
    blocked = set(request.args.get("blocked", "").split(",")) if request.args.get("blocked") else set()
    allowed = set(request.args.get("allowed", "").split(",")) if request.args.get("allowed") else None

    if UF.find(start) != UF.find(goal):
        return render_template(
            "print.html",
            title="No route",
            path="No route available",
            km=0,
            mins=0,
            price=0,
            hops=0,
            table=[],
        )

    blocked.discard(start)
    blocked.discard(goal)

    want = max(1, min(limit, 60))
    paths = search_paths(start, goal, mode, blocked, allowed, max_hops, want)[:limit]
    
    if not paths:
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

    idx = max(1, min(int(option_id), len(paths))) - 1
    path = paths[idx]
    km, mins, price, hops = totals(GD, path)

    table = []
    for leg in legs_list(path):
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
        title=f"{config.APP_NAME}: {start} → {goal} (Option {idx + 1})",
        path=" → ".join(path),
        km=km,
        mins=mins,
        price=price,
        hops=hops,
        table=table,
    )


if __name__ == "__main__":
    app.run(debug=True)