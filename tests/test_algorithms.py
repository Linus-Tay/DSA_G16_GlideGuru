"""
Tests for GlideGuru Algorithms
==============================
Run with: PYTHONPATH=. pytest tests/test_algorithms.py -v -s
note: install pytest
"""
 
import time
import pytest
from glideguru.algorithms import dijkstra, astar, yen_k_paths
from glideguru.data import GraphData, Edge, Carrier, Airport
from glideguru.routing import weight_fn
 
 
# ───────────────────────────────────────────────────────────────────
# FIXTURES — Reusable test data
# ───────────────────────────────────────────────────────────────────
 
@pytest.fixture
def simple_graph():
    """
    Small graph for basic correctness tests.
 
    A ---10km--- B ---10km--- D
    |                        ^
    +---15km--- C ---10km---+
 
    A→B→D = 20km, $200, 120min (shortest distance)
    A→C→D = 25km, $100,  60min (cheapest & fastest)
    """
    airports = {
        "A": Airport(iata="A", name="Airport A", city="City A", country="Country A", lat=0.0, lon=0.0),
        "B": Airport(iata="B", name="Airport B", city="City B", country="Country B", lat=1.0, lon=1.0),
        "C": Airport(iata="C", name="Airport C", city="City C", country="Country C", lat=-1.0, lon=1.0),
        "D": Airport(iata="D", name="Airport D", city="City D", country="Country D", lat=2.0, lon=2.0),
    }
 
    graph = {}
    edge_lookup = {}
 
    def add_edge(u, v, km, price, minutes):
        carrier = Carrier(iata="TS", name="Test Air")
        e = Edge(dest=v, km=km, minutes=minutes, price=price, daily=1, departures=(), carriers=(carrier,))
        graph.setdefault(u, []).append(e)
        edge_lookup.setdefault(u, {})[v] = e
 
    add_edge("A", "B", 10.0, 100.0, 60)
    add_edge("B", "D", 10.0, 100.0, 60)
    add_edge("A", "C", 15.0, 50.0, 30)
    add_edge("C", "D", 10.0, 50.0, 30)
 
    for a in airports:
        graph.setdefault(a, [])
        edge_lookup.setdefault(a, {})
 
    return GraphData(airports=airports, graph=graph, edge_lookup=edge_lookup)
 
 
@pytest.fixture
def airline_graph():
    """
    Graph with multiple airlines for carrier filtering tests.
 
    A ---(SQ)--- B ---(SQ)--- D
    |                         ^
    +---(AA)--- C ---(AA)----+
    """
    airports = {
        "A": Airport(iata="A", name="Airport A", city="City A", country="Country A", lat=0.0, lon=0.0),
        "B": Airport(iata="B", name="Airport B", city="City B", country="Country B", lat=1.0, lon=1.0),
        "C": Airport(iata="C", name="Airport C", city="City C", country="Country C", lat=-1.0, lon=1.0),
        "D": Airport(iata="D", name="Airport D", city="City D", country="Country D", lat=2.0, lon=2.0),
    }
 
    graph = {}
    edge_lookup = {}
 
    def add_edge(u, v, km, price, minutes, airline_code, airline_name):
        carrier = Carrier(iata=airline_code, name=airline_name)
        e = Edge(dest=v, km=km, minutes=minutes, price=price, daily=1, departures=(), carriers=(carrier,))
        graph.setdefault(u, []).append(e)
        edge_lookup.setdefault(u, {})[v] = e
 
    add_edge("A", "B", 10.0, 100.0, 60, "SQ", "Singapore Airlines")
    add_edge("B", "D", 10.0, 100.0, 60, "SQ", "Singapore Airlines")
    add_edge("A", "C", 15.0, 50.0, 30, "AA", "American Airlines")
    add_edge("C", "D", 10.0, 50.0, 30, "AA", "American Airlines")
 
    for a in airports:
        graph.setdefault(a, [])
        edge_lookup.setdefault(a, {})
 
    return GraphData(airports=airports, graph=graph, edge_lookup=edge_lookup)
 
 
# ───────────────────────────────────────────────────────────────────
# DIJKSTRA TESTS
# ───────────────────────────────────────────────────────────────────
 
class TestDijkstra:
 
    def test_cheapest_path(self, simple_graph):
        """Dijkstra should find A→C→D as cheapest (50+50=100 vs 100+100=200)."""
        path, cost = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.price,
            blocked=set(), allowed=None, max_hops=5
        )
        assert path == ["A", "C", "D"]
        assert cost == 100.0
 
    def test_shortest_distance(self, simple_graph):
        """Dijkstra should find A→B→D as shortest distance (10+10=20 vs 15+10=25)."""
        path, cost = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.km,
            blocked=set(), allowed=None, max_hops=5
        )
        assert path == ["A", "B", "D"]
        assert cost == 20.0
 
    def test_fastest_path(self, simple_graph):
        """Dijkstra should find A→C→D as fastest (30+30=60 vs 60+60=120)."""
        path, cost = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.minutes,
            blocked=set(), allowed=None, max_hops=5
        )
        assert path == ["A", "C", "D"]
        assert cost == 60
 
    def test_blocked_airport(self, simple_graph):
        """Blocking B should force the path through C."""
        path, cost = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.km,
            blocked={"B"}, allowed=None, max_hops=5
        )
        assert path == ["A", "C", "D"]
        assert cost == 25.0
 
    def test_blocked_start(self, simple_graph):
        """Blocking the start airport should return no path."""
        path, cost = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.km,
            blocked={"A"}, allowed=None, max_hops=5
        )
        assert path == []
        assert cost == float('inf')
 
    def test_blocked_goal(self, simple_graph):
        """Blocking the goal airport should return no path."""
        path, cost = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.km,
            blocked={"D"}, allowed=None, max_hops=5
        )
        assert path == []
        assert cost == float('inf')
 
    def test_max_hops_limit(self, simple_graph):
        """With max_hops=1, only direct flights should work."""
        path, cost = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.km,
            blocked=set(), allowed=None, max_hops=1
        )
        assert path == []
        assert cost == float('inf')
 
    def test_no_path_exists(self, simple_graph):
        """Searching for a path to a disconnected node should fail."""
        path, cost = dijkstra(
            simple_graph, "D", "A", w=lambda e: e.km,
            blocked=set(), allowed=None, max_hops=5
        )
        assert path == []
        assert cost == float('inf')
 
    def test_airline_filter(self, airline_graph):
        """Filtering to SQ should force the path through B."""
        path, cost = dijkstra(
            airline_graph, "A", "D", w=lambda e: e.km,
            blocked=set(), allowed={"SQ"}, max_hops=5
        )
        assert path == ["A", "B", "D"]
 
    def test_airline_filter_other(self, airline_graph):
        """Filtering to AA should force the path through C."""
        path, cost = dijkstra(
            airline_graph, "A", "D", w=lambda e: e.km,
            blocked=set(), allowed={"AA"}, max_hops=5
        )
        assert path == ["A", "C", "D"]
 
 
# ───────────────────────────────────────────────────────────────────
# A* TESTS
# ───────────────────────────────────────────────────────────────────
 
class TestAStar:
 
    def test_shortest_distance(self, simple_graph):
        """A* should find A→B→D as shortest distance (10+10=20)."""
        path, cost = astar(
            simple_graph, "A", "D",
            blocked=set(), allowed=None, max_hops=5
        )
        assert path == ["A", "B", "D"]
        assert cost == 20.0
 
    def test_matches_dijkstra(self, simple_graph):
        """A* and Dijkstra should find the same shortest distance path."""
        path_astar, cost_astar = astar(
            simple_graph, "A", "D",
            blocked=set(), allowed=None, max_hops=5
        )
        path_dijkstra, cost_dijkstra = dijkstra(
            simple_graph, "A", "D", w=lambda e: e.km,
            blocked=set(), allowed=None, max_hops=5
        )
        assert cost_astar == cost_dijkstra
        assert path_astar == path_dijkstra
 
    def test_blocked_airport(self, simple_graph):
        """Blocking B should force A* through C."""
        path, cost = astar(
            simple_graph, "A", "D",
            blocked={"B"}, allowed=None, max_hops=5
        )
        assert path == ["A", "C", "D"]
        assert cost == 25.0
 
    def test_blocked_start(self, simple_graph):
        """Blocking start should return no path."""
        path, cost = astar(
            simple_graph, "A", "D",
            blocked={"A"}, allowed=None, max_hops=5
        )
        assert path == []
        assert cost == float('inf')
 
    def test_blocked_goal(self, simple_graph):
        """Blocking goal should return no path."""
        path, cost = astar(
            simple_graph, "A", "D",
            blocked={"D"}, allowed=None, max_hops=5
        )
        assert path == []
        assert cost == float('inf')
 
    def test_same_start_and_goal(self, simple_graph):
        """Start == goal should return single-node path with 0 cost."""
        path, cost = astar(
            simple_graph, "A", "A",
            blocked=set(), allowed=None, max_hops=5
        )
        assert path == ["A"]
        assert cost == 0.0
 
    def test_max_hops_limit(self, simple_graph):
        """With max_hops=1, no path should be found (no direct A→D)."""
        path, cost = astar(
            simple_graph, "A", "D",
            blocked=set(), allowed=None, max_hops=1
        )
        assert path == []
        assert cost == float('inf')
 
    def test_airline_filter(self, airline_graph):
        """Filtering to SQ should force A* through B."""
        path, cost = astar(
            airline_graph, "A", "D",
            blocked=set(), allowed={"SQ"}, max_hops=5
        )
        assert path == ["A", "B", "D"]
 
    def test_airline_filter_other(self, airline_graph):
        """Filtering to AA should force A* through C."""
        path, cost = astar(
            airline_graph, "A", "D",
            blocked=set(), allowed={"AA"}, max_hops=5
        )
        assert path == ["A", "C", "D"]
 
    def test_no_path_exists(self, simple_graph):
        """A* should return empty when no path exists."""
        path, cost = astar(
            simple_graph, "D", "A",
            blocked=set(), allowed=None, max_hops=5
        )
        assert path == []
        assert cost == float('inf')
 
    def test_blocked_edges(self, simple_graph):
        """Blocking A→B edge should force path through C."""
        path, cost = astar(
            simple_graph, "A", "D",
            blocked=set(), allowed=None, max_hops=5,
            blocked_edges={("A", "B")}
        )
        assert path == ["A", "C", "D"]
        assert cost == 25.0
 
 
# ───────────────────────────────────────────────────────────────────
# YEN'S K-PATHS TESTS
# ───────────────────────────────────────────────────────────────────
 
class TestYenKPaths:
 
    def test_finds_two_paths_dijkstra(self, simple_graph):
        """Yen's with Dijkstra should find both paths ranked by distance."""
        paths = yen_k_paths(
            simple_graph, "A", "D", w=lambda e: e.km, k=2,
            blocked=set(), allowed=None, max_hops=5, use_astar=False
        )
        assert len(paths) == 2
        assert paths[0] == ["A", "B", "D"]  # 20km
        assert paths[1] == ["A", "C", "D"]  # 25km
 
    def test_finds_two_paths_astar(self, simple_graph):
        """Yen's with A* should find the same paths as with Dijkstra."""
        paths = yen_k_paths(
            simple_graph, "A", "D", w=lambda e: e.km, k=2,
            blocked=set(), allowed=None, max_hops=5, use_astar=True
        )
        assert len(paths) == 2
        assert paths[0] == ["A", "B", "D"]  # 20km
        assert paths[1] == ["A", "C", "D"]  # 25km
 
    def test_cheapest_mode(self, simple_graph):
        """Yen's with price weight should rank A→C→D first (cheapest)."""
        w = weight_fn("Cheapest")
        paths = yen_k_paths(
            simple_graph, "A", "D", w=w, k=2,
            blocked=set(), allowed=None, max_hops=5
        )
        assert paths[0] == ["A", "C", "D"]  # 50+50=100
        assert paths[1] == ["A", "B", "D"]  # 100+100=200
 
    def test_k_exceeds_available_paths(self, simple_graph):
        """Requesting more paths than exist should return only what's available."""
        paths = yen_k_paths(
            simple_graph, "A", "D", w=lambda e: e.km, k=10,
            blocked=set(), allowed=None, max_hops=5
        )
        assert len(paths) == 2  # only 2 paths exist
 
 
# ───────────────────────────────────────────────────────────────────
# REAL DATASET — Path correctness and timing
# ───────────────────────────────────────────────────────────────────
 
class TestRealDataset:
    """
    Tests against the actual airline_routes_with_price.json dataset.
    Shows the paths found and benchmarks A* vs Dijkstra.
    Skipped if the file is not found.
    """
 
    @pytest.fixture(autouse=True)
    def load_real_data(self):
        from pathlib import Path
        from glideguru.data import load_graph
        import glideguru.config as config
 
        data_path = config.DATA_PATH
        if not Path(data_path).exists():
            pytest.skip("Real dataset not found")
        self.gd = load_graph(data_path)
 
    def test_sin_to_jfk_astar(self):
        """A* should find a valid shortest distance path from SIN to JFK."""
        t0 = time.perf_counter()
        path, cost = astar(
            self.gd, "SIN", "JFK",
            blocked=set(), allowed=None, max_hops=5
        )
        elapsed = (time.perf_counter() - t0) * 1000
 
        print(f"\n  A* SIN → JFK:")
        print(f"  Path:     {' → '.join(path)}")
        print(f"  Distance: {cost:,.0f} km")
        print(f"  Time:     {elapsed:.2f} ms")
 
        assert len(path) >= 2
        assert path[0] == "SIN"
        assert path[-1] == "JFK"
        assert cost < float('inf')
 
    def test_sin_to_jfk_dijkstra(self):
        """Dijkstra should find a valid shortest distance path from SIN to JFK."""
        t0 = time.perf_counter()
        path, cost = dijkstra(
            self.gd, "SIN", "JFK", w=lambda e: e.km,
            blocked=set(), allowed=None, max_hops=5
        )
        elapsed = (time.perf_counter() - t0) * 1000
 
        print(f"\n  Dijkstra SIN → JFK:")
        print(f"  Path:     {' → '.join(path)}")
        print(f"  Distance: {cost:,.0f} km")
        print(f"  Time:     {elapsed:.2f} ms")
 
        assert len(path) >= 2
        assert path[0] == "SIN"
        assert path[-1] == "JFK"
 
    def test_sin_to_jfk_both_match(self):
        """A* and Dijkstra should find the same optimal distance for SIN→JFK."""
        path_astar, cost_astar = astar(
            self.gd, "SIN", "JFK",
            blocked=set(), allowed=None, max_hops=5
        )
        path_dijkstra, cost_dijkstra = dijkstra(
            self.gd, "SIN", "JFK", w=lambda e: e.km,
            blocked=set(), allowed=None, max_hops=5
        )
 
        print(f"\n  A*:       {' → '.join(path_astar)} = {cost_astar:,.0f} km")
        print(f"  Dijkstra: {' → '.join(path_dijkstra)} = {cost_dijkstra:,.0f} km")
 
        assert abs(cost_astar - cost_dijkstra) < 0.01
 
    def test_sin_to_lhr_timing(self):
        """Benchmark A* vs Dijkstra on SIN→LHR."""
        runs = 20
 
        t0 = time.perf_counter()
        for _ in range(runs):
            path_d, cost_d = dijkstra(
                self.gd, "SIN", "LHR", w=lambda e: e.km,
                blocked=set(), allowed=None, max_hops=5
            )
        dijkstra_time = (time.perf_counter() - t0) / runs * 1000
 
        t0 = time.perf_counter()
        for _ in range(runs):
            path_a, cost_a = astar(
                self.gd, "SIN", "LHR",
                blocked=set(), allowed=None, max_hops=5
            )
        astar_time = (time.perf_counter() - t0) / runs * 1000
 
        print(f"\n  SIN → LHR ({runs} runs avg):")
        print(f"  Dijkstra: {' → '.join(path_d)} = {cost_d:,.0f} km  |  {dijkstra_time:.2f} ms")
        print(f"  A*:       {' → '.join(path_a)} = {cost_a:,.0f} km  |  {astar_time:.2f} ms")
        print(f"  Speedup:  {dijkstra_time / astar_time:.2f}x")
 
    def test_sin_to_jfk_timing(self):
        """Benchmark A* vs Dijkstra on SIN→JFK."""
        runs = 20
 
        t0 = time.perf_counter()
        for _ in range(runs):
            path_d, cost_d = dijkstra(
                self.gd, "SIN", "JFK", w=lambda e: e.km,
                blocked=set(), allowed=None, max_hops=5
            )
        dijkstra_time = (time.perf_counter() - t0) / runs * 1000
 
        t0 = time.perf_counter()
        for _ in range(runs):
            path_a, cost_a = astar(
                self.gd, "SIN", "JFK",
                blocked=set(), allowed=None, max_hops=5
            )
        astar_time = (time.perf_counter() - t0) / runs * 1000
 
        print(f"\n  SIN → JFK ({runs} runs avg):")
        print(f"  Dijkstra: {' → '.join(path_d)} = {cost_d:,.0f} km  |  {dijkstra_time:.2f} ms")
        print(f"  A*:       {' → '.join(path_a)} = {cost_a:,.0f} km  |  {astar_time:.2f} ms")
        print(f"  Speedup:  {dijkstra_time / astar_time:.2f}x")
 
    def test_lax_to_nrt_timing(self):
        """Benchmark A* vs Dijkstra on LAX→NRT."""
        runs = 20
 
        t0 = time.perf_counter()
        for _ in range(runs):
            path_d, cost_d = dijkstra(
                self.gd, "LAX", "NRT", w=lambda e: e.km,
                blocked=set(), allowed=None, max_hops=5
            )
        dijkstra_time = (time.perf_counter() - t0) / runs * 1000
 
        t0 = time.perf_counter()
        for _ in range(runs):
            path_a, cost_a = astar(
                self.gd, "LAX", "NRT",
                blocked=set(), allowed=None, max_hops=5
            )
        astar_time = (time.perf_counter() - t0) / runs * 1000
 
        print(f"\n  LAX → NRT ({runs} runs avg):")
        print(f"  Dijkstra: {' → '.join(path_d)} = {cost_d:,.0f} km  |  {dijkstra_time:.2f} ms")
        print(f"  A*:       {' → '.join(path_a)} = {cost_a:,.0f} km  |  {astar_time:.2f} ms")
        print(f"  Speedup:  {dijkstra_time / astar_time:.2f}x")
 
    def test_yen_shortest_returns_ranked(self):
        """Yen's with A* should return paths ranked by distance."""
        t0 = time.perf_counter()
        paths = yen_k_paths(
            self.gd, "SIN", "JFK", w=lambda e: e.km, k=5,
            blocked=set(), allowed=None, max_hops=5, use_astar=True
        )
        elapsed = (time.perf_counter() - t0) * 1000
 
        print(f"\n  Yen's + A* SIN → JFK (k=5) in {elapsed:.2f} ms:")
        distances = []
        for i, p in enumerate(paths):
            total_km = sum(
                self.gd.edge_lookup[p[j]][p[j + 1]].km
                for j in range(len(p) - 1)
            )
            distances.append(total_km)
            print(f"  {i+1}. {' → '.join(p)} = {total_km:,.0f} km")
 
        assert len(paths) >= 2
 
        # Verify distances are in ascending order
        for i in range(len(distances) - 1):
            assert distances[i] <= distances[i + 1], (
                f"Path {i} ({distances[i]:.0f} km) should be <= "
                f"Path {i+1} ({distances[i+1]:.0f} km)"
            )
 