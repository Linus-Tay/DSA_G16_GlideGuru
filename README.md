# GlideGuru - Flight Routing Application

**Beautiful flight routing — shortest, cheapest, smartest.**

A flight routing web application that finds optimal flight paths based on distance, time, cost, and connections.

---

## Quick Start

### Installation

```bash
# Navigate to project
cd DSA_G16_GlideGuru

# Create virtual environment (optional)
python -m venv venv
venv\Scripts\activate  # Windows
# OR source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Run the App

```bash
python app.py
```

Open browser to: **http://127.0.0.1:5000**

---

## Project Structure

```
DSA_G16_GlideGuru/
├── app.py                              # Flask server & API routes
├── requirements.txt                    # Dependencies (flask, pandas)
├── README.md                           # This file
│
├── glideguru/                          # Core package
│   ├── config.py                       # App constants & settings
│   ├── data.py                         # Graph data structures
│   ├── algorithms.py                   # Pathfinding algorithms (BFS, Dijkstra, Yen's K-paths, A*, Bidirectional)
│   ├── routing.py                      # Routing modes & weight functions
│   ├── nearby.py                       # Nearby airport utilities
│   └── unionfind.py                    # Union-Find data structure
│
├── templates/                          # HTML templates
│   ├── base.html                       # Base layout
│   ├── index.html                      # Main search interface
│   └── print.html                      # Print-friendly itinerary
│
├── static/                             # Frontend assets
│   ├── app.js                          # JavaScript logic
│   └── app.css                         # Styling
│
├── data/
│   └── airline_routes_with_price.json  # Airport & route dataset
│
└── tests/                              # Unit & integration tests
    ├── test_algorithms.py
    ├── test_app.py
    ├── test_yen.py
    └── test_backend_random_search_*.py
```

---

## File Descriptions

### Root Files

**app.py** — Main Flask application  
- Loads data at startup
- Handles routes: `/` (main page), `/api/search` (compute routes), `/print` (itinerary view)
- Orchestrates pathfinding algorithms

**requirements.txt** — Python dependencies  
- `flask` — web framework
- `pandas` — data manipulation

### Backend (glideguru/)

**config.py** — Configuration constants  
- `APP_NAME`, `TAGLINE`, `DATA_PATH`
- `DEFAULT_MAX_HOPS = 4`, `DEFAULT_TOP_K = 3`

**data.py** — Data structures and loading  
- Classes: `Airport`, `Carrier`, `Edge`, `GraphData`
- Function: `load_graph()` loads JSON into memory-efficient graph

**algorithms.py** — Pathfinding algorithms  
- `bfs_hops()` — Minimum hops (BFS)
- `dijkstra()` — Shortest path by weight
- `yen_k_paths()` — K shortest paths
- `astar()` — A* with heuristics
- `bidirectional_dijkstra()` — Bidirectional search

**routing.py** — Routing modes and scoring  
- `weight_fn(mode)` returns optimization function
- Modes: Shortest, Fastest, Cheapest, Fewest Connections, Cost-effective
- Functions: `totals()`, `score_of()`, `legs_df()`

**nearby.py** — Nearby airport utilities  
- `get_nearby_viable_swaps()` finds alternative routes using nearby airports

**unionfind.py** — Union-Find data structure  
- Checks if airports are in same connected component
- Used for connectivity verification

### Frontend (templates/ & static/)

**base.html** — Base HTML layout (header, nav, footer)

**index.html** — Main search interface  
- Search form, filters, map, route cards, leg details

**print.html** — Print-optimized itinerary view

**app.js** — Client-side logic  
- `searchFlights()` — POST to `/api/search`
- `displayResults()` — Render route cards
- `renderMap()` — Visualize on Leaflet map

**app.css** — Styling (responsive design for mobile/tablet/desktop)

### Data

**airline_routes_with_price.json** — Dataset containing airports and flight routes

---

## How It Works

1. User selects origin, destination, mode (Shortest/Fastest/Cheapest/etc.), and constraints
2. Frontend sends POST request to `/api/search`
3. Backend uses BFS or Dijkstra's algorithm to find routes, constrained by:
   - Blocked airports
   - Allowed airlines
   - Maximum hops
4. Returns TOP_K routes with metrics (km, minutes, price, hops)
5. Frontend displays interactive map, route cards, and leg details
6. User can print or export itinerary

---

## Customization

### Add New Routing Mode

**1. Edit `glideguru/routing.py`:**
```python
def weight_fn(mode: str) -> Callable[[Edge], float]:
    if mode == "MyMode":
        return lambda e: e.price * 0.5 + e.km * 0.5
    # ... other modes
```

**2. Add option to `templates/index.html`:**
```html
<option value="MyMode">My Mode</option>
```

### Modify Algorithm Constraints

Edit `glideguru/algorithms.py` to change:
- Max hops enforcement
- Airline filtering
- Blocked airport handling

### Add Fields to Route Response

**1. Edit `app.py` function `legs_list()`:**
```python
legs.append({
    # ... existing fields ...
    'new_field': value  # NEW
})
```

**2. Update `static/app.js` function `renderDetails()`** to display the new field

### Update UI

- **Layout:** `templates/index.html`
- **Behavior:** `static/app.js`
- **Styling:** `static/app.css`

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_algorithms.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=glideguru
```

---

## Troubleshooting

**Flask not found?**
```bash
pip install -r requirements.txt
```

**Port 5000 already in use?**
```bash
# Windows: netstat -ano | findstr :5000
# Kill process or use different port: flask run --port 5001
```

**Data file missing?**
- Verify `data/airline_routes_with_price.json` exists
- Check it's valid JSON: `python -m json.tool data/airline_routes_with_price.json`

**Search returns no results?**
- Check airport codes are uppercase
- Verify airports exist in dataset
- Try removing airline/airport filters
- Test connectivity: Are source and destination reachable?

---

## Team Info

**Project:** GlideGuru Flight Routing  
**Group:** DSA_G16  
**Purpose:** Data Structures & Algorithms Final Project

---

## References

- Flask: https://flask.palletsprojects.com/
- Dijkstra: https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
- Yen's Algorithm: https://en.wikipedia.org/wiki/Yen%27s_algorithm
- Leaflet.js: https://leafletjs.com/
