from flask import Flask, render_template, request, jsonify
import glideguru.config as config
from glideguru.data import load_graph, all_carrier_codes
from glideguru.algorithms import bfs_hops, yen_k_paths
from glideguru.routing import totals, weight_fn, score_of

app = Flask(__name__)

GD = load_graph(config.DATA_PATH)
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


@app.get("/")
def index():
    airports = [
        {"code": c, "label": airport_label(c), "lat": AIRPORTS[c].lat, "lon": AIRPORTS[c].lon}
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

    if not start or not goal or start == goal:
        return jsonify({"error": "Invalid start/goal"}), 400

    blocked.discard(start)
    blocked.discard(goal)

    want = max(1, min(limit + 1, 60))  # safety cap

    if mode == "Fewest hops":
        paths: list[list[str]] = []
        p = bfs_hops(GD, start, goal, blocked, allowed, max_hops=max_hops)
        if p:
            paths.append(p)

        alt = yen_k_paths(
            GD, start, goal, weight_fn("Cost-effective"),
            k=want, blocked=blocked, allowed=allowed, max_hops=max_hops
        )
        for x in alt:
            if x not in paths:
                paths.append(x)

        has_more = len(paths) > limit
        paths = paths[:limit]
        wf = weight_fn("Fewest hops")
    else:
        wf = weight_fn(mode)
        paths = yen_k_paths(GD, start, goal, wf, k=want, blocked=blocked, allowed=allowed, max_hops=max_hops)
        has_more = len(paths) > limit
        paths = paths[:limit]

    options = []
    for i, p in enumerate(paths, 1):
        km, mins, price, hops = totals(GD, p)
        options.append(
            {
                "id": i,
                "path": p,
                "km": float(km),
                "minutes": int(mins),
                "price": float(price),
                "hops": int(hops),
                "score": float(score_of(GD, p, wf)),
                "legs": legs_list(p),
            }
        )

    return jsonify({"options": options, "has_more": has_more})


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

    blocked.discard(start)
    blocked.discard(goal)

    want = max(1, min(limit, 60))

    if mode == "Fewest hops":
        paths: list[list[str]] = []
        p = bfs_hops(GD, start, goal, blocked, allowed, max_hops=max_hops)
        if p:
            paths.append(p)
        alt = yen_k_paths(GD, start, goal, weight_fn("Cost-effective"), k=want, blocked=blocked, allowed=allowed, max_hops=max_hops)
        for x in alt:
            if x not in paths:
                paths.append(x)
        paths = paths[:limit]
    else:
        paths = yen_k_paths(GD, start, goal, weight_fn(mode), k=want, blocked=blocked, allowed=allowed, max_hops=max_hops)

    if not paths:
        return render_template("print.html", title=f"{config.APP_NAME}: No route", path="No route", km=0, mins=0, price=0, hops=0, table=[])

    idx = max(1, min(int(option_id), len(paths))) - 1
    path = paths[idx]
    km, mins, price, hops = totals(GD, path)

    # print uses leg list for the table (simple)
    table = []
    for leg in legs_list(path):
        airline_names = ", ".join([a["name"] for a in leg["airlines"] if a.get("name")]) or "Unknown"
        airline_codes = ", ".join([a["code"] for a in leg["airlines"] if a.get("code")]) or "—"
        table.append({
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
        })

    return render_template(
        "print.html",
        title=f"{config.APP_NAME}: {start} → {goal} (Option {idx+1})",
        path=" → ".join(path),
        km=km,
        mins=mins,
        price=price,
        hops=hops,
        table=table,
    )


if __name__ == "__main__":
    app.run(debug=True)