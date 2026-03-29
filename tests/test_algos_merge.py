import sys
import os
import unittest

# 1. TELL PYTHON WHERE THE FOLDER IS FIRST
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. NOW DO THE IMPORTS
from glideguru.data import GraphData, Edge, Airport
from glideguru.algorithms import yen_k_paths

class TestYenMerge(unittest.TestCase):
    def setUp(self):
        # 1. Define the mock airports first
        airports = {
            "AAA": Airport(iata="AAA", name="A", city="A", country="A", lat=0.0, lon=0.0),
            "BBB": Airport(iata="BBB", name="B", city="B", country="B", lat=1.0, lon=1.0),
            "CCC": Airport(iata="CCC", name="C", city="C", country="C", lat=1.0, lon=-1.0),
            "DDD": Airport(iata="DDD", name="D", city="D", country="D", lat=2.0, lon=0.0),
        }
        
        # 2. Define the mock edges
        # 2. Define the mock edges (now with departures=[])
        e1 = Edge(dest="BBB", km=100, minutes=60, price=100, daily=1, carriers=[], departures=[])
        e2 = Edge(dest="DDD", km=100, minutes=60, price=100, daily=1, carriers=[], departures=[])
        e3 = Edge(dest="CCC", km=150, minutes=90, price=150, daily=1, carriers=[], departures=[])
        e4 = Edge(dest="DDD", km=100, minutes=60, price=100, daily=1, carriers=[], departures=[])
        
        # 3. Define the graph and lookup structures
        graph = {
            "AAA": [e1, e3],
            "BBB": [e2],
            "CCC": [e4],
            "DDD": []
        }
        
        edge_lookup = {
            "AAA": {"BBB": e1, "CCC": e3},
            "BBB": {"DDD": e2},
            "CCC": {"DDD": e4},
            "DDD": {}
        }

        # 4. Now pass all three into the constructor
        self.gd = GraphData(airports, graph, edge_lookup)
        
        # Simple weight function returning price
        self.w = lambda e: float(e.price)

    def test_yen_with_dijkstra(self):
        """Test Yen's algorithm using standard Dijkstra (Cost-effective mode)."""
        paths = yen_k_paths(
            self.gd, start="AAA", goal="DDD", w=self.w, k=2, 
            blocked=set(), allowed=None, max_hops=3, use_astar=False
        )
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0], ["AAA", "BBB", "DDD"])
        self.assertEqual(paths[1], ["AAA", "CCC", "DDD"])

    def test_yen_with_astar(self):
        """Test Yen's algorithm using Adam's A* (Shortest mode)."""
        paths = yen_k_paths(
            self.gd, start="AAA", goal="DDD", w=self.w, k=2, 
            blocked=set(), allowed=None, max_hops=3, use_astar=True
        )
        # It should still find both paths without crashing
        self.assertEqual(len(paths), 2)
        
    def test_dijkstra_hop_trap(self):
        """
        Tests if the algorithm correctly handles the Resource-Constrained 
        Shortest Path Problem (max_hops) without prematurely discarding 
        more expensive, but hop-efficient paths.
        """
        # 1. Setup Trap Airports
        trap_airports = {
            "START": Airport(iata="START", name="Start", city="S", country="S", lat=0.0, lon=0.0),
            "DETOUR": Airport(iata="DETOUR", name="Detour", city="D", country="D", lat=1.0, lon=1.0),
            "MID": Airport(iata="MID", name="Middle", city="M", country="M", lat=2.0, lon=2.0),
            "GOAL": Airport(iata="GOAL", name="Goal", city="G", country="G", lat=3.0, lon=3.0),
        }

        # 2. Setup Trap Edges
        # START -> DETOUR (Cost 10)
        e_start_detour = Edge(dest="DETOUR", km=100, minutes=60, price=10, daily=1, carriers=[], departures=[])
        # DETOUR -> MID (Cost 10) - Cumulative cost to MID = 20 (Cheaper, but 2 hops!)
        e_detour_mid = Edge(dest="MID", km=100, minutes=60, price=10, daily=1, carriers=[], departures=[])
        
        # START -> MID (Cost 50) - Cumulative cost to MID = 50 (More expensive, but only 1 hop!)
        e_start_mid = Edge(dest="MID", km=100, minutes=60, price=50, daily=1, carriers=[], departures=[])
        
        # MID -> GOAL (Cost 10)
        e_mid_goal = Edge(dest="GOAL", km=100, minutes=60, price=10, daily=1, carriers=[], departures=[])

        # 3. Build Trap Graph
        trap_graph = {
            "START": [e_start_detour, e_start_mid],
            "DETOUR": [e_detour_mid],
            "MID": [e_mid_goal],
            "GOAL": []
        }
        
        trap_lookup = {
            "START": {"DETOUR": e_start_detour, "MID": e_start_mid},
            "DETOUR": {"MID": e_detour_mid},
            "MID": {"GOAL": e_mid_goal},
            "GOAL": {}
        }

        # Inject trap data into a fresh GraphData instance
        trap_gd = GraphData(trap_airports, trap_graph, trap_lookup)

        # 4. RUN THE TRAP
        # We strictly limit it to 2 hops. 
        paths = yen_k_paths(
            trap_gd, start="START", goal="GOAL", w=self.w, k=1, 
            blocked=set(), allowed=None, max_hops=2, use_astar=False
        )

        # If the array is empty (len == 0), the algorithm fell for the trap!
        self.assertGreater(len(paths), 0, "Algorithm fell for the Dijkstra Hop Trap! It returned no routes.")
        
        # If it passed, it should have found the more expensive, 2-hop route.
        self.assertEqual(paths[0], ["START", "MID", "GOAL"])

if __name__ == '__main__':
    unittest.main()