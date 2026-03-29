import unittest
from glideguru.algorithms import yen_k_paths
from glideguru.data import GraphData, Edge, Carrier
from glideguru.routing import weight_fn, score_of

class TestYenAlgorithm(unittest.TestCase):
    def setUp(self):
        # 1. Build the data structures first
        airports = {"A": None, "B": None, "C": None, "D": None}
        graph = {}
        edge_lookup = {}
        
        def add_edge(u, v, price, minutes):
            e = Edge(dest=v, km=100, minutes=minutes, price=price, daily=1, departures=[], carriers=[])
            graph.setdefault(u, []).append(e)
            edge_lookup.setdefault(u, {})[v] = e

        add_edge("A", "B", 10.0, 60)
        add_edge("B", "D", 10.0, 60)
        add_edge("A", "C", 15.0, 60)
        add_edge("C", "D", 10.0, 60)

        # 2. Instantiate the frozen dataclass once with everything ready
        self.gd = GraphData(airports=airports, graph=graph, edge_lookup=edge_lookup)

    def test_finds_multiple_paths(self):
        # Using "Cheapest" mode
        w = weight_fn("Cheapest")
        paths = yen_k_paths(self.gd, "A", "D", w, k=2, blocked=set(), allowed=None, max_hops=3)
        
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0], ["A", "B", "D"])  # Best
        self.assertEqual(paths[1], ["A", "C", "D"])  # 2nd Best

    def test_cost_effective_diversity(self):
        # Using your "Cost-effective" formula
        w = weight_fn("Cost-effective")
        paths = yen_k_paths(self.gd, "A", "D", w, k=2, blocked=set(), allowed=None, max_hops=3)
        
        # Verify the scores are actually different
        score1 = score_of(self.gd, paths[0], w)
        score2 = score_of(self.gd, paths[1], w)
        self.assertTrue(score1 < score2)

if __name__ == "__main__":
    unittest.main()