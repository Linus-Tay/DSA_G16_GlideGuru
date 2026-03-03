# GlideGuru

Beautiful flight routing — shortest, cheapest, smartest.

---

## How to run

```bash
pip install -r requirements.txt
python app.py
```

#### Open: http://127.0.0.1:5000

---

# Project Structure

## Backend
- app.py — Flask server + API routes (/, /api/search, /print) and response shaping.
- glideguru/config.py — App constants (name/tagline), data path, and default settings.
- glideguru/data.py — Loads airline_routes_with_price.json into GraphData (airports + edges).
- glideguru/routing.py — Weight functions + totals/scoring helpers (km/mins/price/hops, route score).
- glideguru/algorithms.py — Contains bfs_hops, dijkstra, yen_k_paths.

## Frontend
- templates/base.html — Shared base layout + loads app.css and app.js.
- templates/index.html — Main UI page (form, map, options, details, filter lists).
- templates/print.html — Print-friendly itinerary page.
- static/app.js — UI logic (map rendering, search request, route cards, leg details, filters).
- static/app.css — Styling for cards, layout, filters, details, legs, and responsive UI.

## Data
- data/airline_routes_with_price.json — Airports + routes dataset used by load_graph().

---

## How Routing Works (High-Level)

1. **UI sends a POST request** to `/api/search` with:
   * `start`, `goal`
   * `mode` (Shortest / Fastest / Cheapest / Cost-effective / Fewest hops)
   * `max_hops`
   * Blocked airports (avoid list)
   * Allowed airline codes
2. **Backend computes routes** using:
   * `bfs_hops()` for the single best “fewest hops” path.
   * `yen_k_paths()` for top-k alternatives (built on `dijkstra()`).
3. **Backend returns route options** with:
   * `path` (list of IATA codes)
   * `km`, `minutes`, `price`, `hops`, `score`
   * `legs` (per-leg details used in UI)
4. **Frontend renders:**
   * Clickable route option cards.
   * A selected route map polyline.
   * Leg-by-leg rows + “Print itinerary” link.

---

## Where to Change Algorithms

### Add or Change Routing Modes
**Go to:** `glideguru/routing.py` → `weight_fn(mode)`
* This function decides what Dijkstra/Yen optimizes.
* *Example:* “Fastest” uses minutes, “Cheapest” uses price.

**If you add a new mode:**
1. Add it to `weight_fn()`.
2. Add the mode option in `templates/index.html` (dropdown).
3. The frontend will automatically send it via `mode`.

### Change Pathfinding Logic
**Go to:** your algorithms file (`bfs_hops`, `dijkstra`, `yen_k_paths`)
* **Common edits:**
  * Enforce stricter `max_hops`.
  * Change how allowed carriers are applied (`_allows()`).
  * Adjust Yen’s candidate selection / duplicate filtering.

---

## Where to Change Backend API Output

**Go to:** `app.py`
* `/api/search` builds the JSON that the UI consumes.
* `legs_list(path)` controls what each leg includes (airlines, departures, km, minutes, etc.).

> **Note:** If you add new fields to `legs_list()`, you must also update `static/app.js` → `renderDetails()` to display them.

---

## Where to Update the UI

### Update Layout / HTML Structure
**Go to:** `templates/index.html`
* Controls the page skeleton (filters panel, map container, option list, details panel).

### Update UI Behavior (Search, Rendering, Map)
**Go to:** `static/app.js`
* **Key functions:**
  * `search()` — Calls `/api/search` and updates the page.
  * `renderOptions()` — Draws the list of route option cards.
  * `selectOption()` — Selects a route and updates map + details.
  * `drawRoute()` — Draws the polyline + markers on the Leaflet map.
  * `renderDetails()` — Builds leg rows + print link.
  * `initFilterLists()` — Handles avoid airports + allowed airlines checkbox lists.

### Update Styling / Theme
**Go to:** `static/app.css`
* Controls cards, pills, detail grid, legs layout, filter items, and responsive rules.

---

## Print View

The **“Print itinerary”** button opens `/print` (server-rendered HTML) using `templates/print.html`.

**If you want print to show more/less columns:**
1. Edit the table generation in `app.py` (inside `/print`).
2. Edit the layout in `templates/print.html`.

---

## ⚠️ Notes for Teammates

* **Do not rename keys** in the `/api/search` response unless you also update `static/app.js`.
* The dataset is loaded once at startup (`GD = load_graph(...)`). **Restart the server** after changing data.
* `allowed airline codes` filter routes by edge carriers; `blocked` removes airports from consideration entirely.
