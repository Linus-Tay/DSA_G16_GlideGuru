import heapq
import math 
from collections import deque
from typing import Callable, Dict, List, Optional, Set, Tuple
from glideguru.data import Edge, GraphData, IATA

def _allows(edge: Edge, allowed: Optional[Set[str]]) -> bool:
    return (not allowed) or any(c.iata in allowed for c in edge.carriers)

def bfs_hops(
    gd: GraphData,
    start: IATA,
    goal: IATA,
    blocked: Set[IATA],
    allowed: Optional[Set[str]],
    max_hops: int,
) -> List[IATA]:
    """
    Finds the path with the fewest number of hops using Breadth-First Search.

    Because BFS explores the graph level by level, the first time the goal is
    reached we are guaranteed to have found a minimum-hop path, subject to the
    current airport/carrier constraints.
    """
    if start in blocked or goal in blocked:
        return []

    q = deque([start])
    prev: Dict[IATA, Optional[IATA]] = {start: None}
    depth: Dict[IATA, int] = {start: 0}

    while q:
        u = q.popleft()
        if u == goal:
            break

        for e in gd.graph.get(u, []):
            v = e.dest

            if v in blocked or v in prev:
                continue

            real_edge = gd.edge_lookup[u].get(v)
            if not real_edge or not _allows(real_edge, allowed):
                continue

            next_depth = depth[u] + 1
            if next_depth > max_hops:
                continue

            prev[v] = u
            depth[v] = next_depth
            q.append(v)

    if goal not in prev:
        return []

    path: List[IATA] = []
    cur: Optional[IATA] = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]

    return list(reversed(path))


def dijkstra(   # to return list of paths and total cost)
    gd: GraphData, 
    start: IATA, 
    goal: IATA, 
    w: Callable[[Edge], float], 
    blocked: Set[IATA], 
    allowed: Optional[Set[str]], 
    max_hops: int,
    blocked_edges: Optional[Set[Tuple[IATA, IATA]]] = None
) -> Tuple[List[IATA], float]:
    """
    Baseline Dijkstra stub for Yen's Algorithm testing.
    Returns (path_list, total_cost).
    """
    if start in blocked or goal in blocked: 
        return [], float('inf')
    
    # Priority queue stores: (accumulated_cost, hops_taken, current_node, path_history)
    pq = [(0.0, 0, start, [start])]
    visited: Dict[IATA, float] = {}
    blocked_edges = blocked_edges or set()

    while pq:
        cost, hops, u, path = heapq.heappop(pq)
        
        # If we reached the destination, return the path and its cost
        if u == goal:
            return path, cost
            
        # If we've found a cheaper way to this node already, skip it
        if u in visited and visited[u] <= cost:
            continue
        visited[u] = cost
        
        # Stop exploring this branch if it exceeds the max connections
        if hops >= max_hops:
            continue
            
        # Explore neighbors
        for edge in gd.graph.get(u, []):
            v = edge.dest
            
            # 1. Check if node or specific edge is blocked (Crucial for Yen's)
            if v in blocked or (u, v) in blocked_edges:
                continue
                
            # 2. Check airline constraints
            if allowed is not None and not any(c.iata in allowed for c in edge.carriers):
                continue
                
            # Calculate new cost using the dynamic weight function w()
            new_cost = cost + float(w(edge))
            heapq.heappush(pq, (new_cost, hops + 1, v, path + [v]))
            
    # Return empty if no path exists
    return [], float('inf')

# A* algorithm using haversine heuristic (shortest distance in km)
_EARTH_RADIUS_KM = 6_371.0

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = (math.radians(x) for x in (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    a = min(1.0, max(0.0, a))
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))

def astar(
    gd: GraphData, start: IATA, goal: IATA, blocked: Set[IATA], allowed: Optional[Set[str]],
    max_hops: int, blocked_edges: Optional[Set[Tuple[IATA, IATA]]] = None,
) -> Tuple[List[IATA], float]:

    if start in blocked or goal in blocked:
        return [], float('inf')
    
    if start == goal:
        return [start], 0.0
    
    blocked_edges = blocked_edges or set()

    # Build heuristic: straight-line km from any airport to the goal
    goal_airport = gd.airports.get(goal)
    if not goal_airport:
        return [], float('inf')
    
    goal_lat = goal_airport.lat
    goal_lon = goal_airport.lon

    def h(airport_code: IATA) -> float:
        airport = gd.airports.get(airport_code)
        if not airport:
            return 0.0
        return _haversine(airport.lat, airport.lon, goal_lat, goal_lon)
    
    # Priority queue: (f_score, counter, g_score, hops, node)
    # counter prevents heapq from comparing IATA strings on ties
    counter = 0
    open_set: List[Tuple[float, int, float, int, IATA]] = []
    heapq.heappush(open_set, (h(start), counter, 0.0, 0, start))
    counter += 1

    # Best known g-score for each node
    g_score: Dict[IATA, float] = {start: 0.0}
 
    # Predecessor map for path reconstruction (memory-efficient)
    prev: Dict[IATA, Optional[IATA]] = {start: None}
 
    # Closed set — consistent heuristic means no re-opening needed
    closed: Set[IATA] = set()

    while open_set:
        f, _, g, hops, current = heapq.heappop(open_set)
 
        # Goal reached — first pop is guaranteed optimal with consistent heuristic
        if current == goal:
            return _reconstruct_path(prev, goal), g
 
        if current in closed:
            continue
        closed.add(current)
 
        if hops >= max_hops:
            continue
 
        for edge in gd.graph.get(current, []):
            neighbor = edge.dest
 
            if neighbor in blocked or neighbor in closed:
                continue
 
            if (current, neighbor) in blocked_edges:
                continue
 
            if allowed is not None:
                if not any(c.iata in allowed for c in edge.carriers):
                    continue
 
            tentative_g = g + edge.km
 
            if tentative_g < g_score.get(neighbor, float('inf')):
                g_score[neighbor] = tentative_g
                prev[neighbor] = current
 
                f_score = tentative_g + h(neighbor)
                heapq.heappush(open_set, (f_score, counter, tentative_g, hops + 1, neighbor))
                counter += 1
 
    return [], float('inf')

def _reconstruct_path(prev: Dict[IATA, Optional[IATA]], goal: IATA) -> List[IATA]:
    """Walk backwards through predecessor map to rebuild the full path."""
    path: List[IATA] = []
    current: Optional[IATA] = goal
    while current is not None:
        path.append(current)
        current = prev[current]
    path.reverse()
    return path




def yen_k_paths(
    gd: GraphData, start: IATA, goal: IATA, w: Callable[[Edge], float], k: int,
    blocked: Set[IATA], allowed: Optional[Set[str]], max_hops: int, use_astar: bool = False
) -> List[List[IATA]]:

    # if use_astar=True when search algorithm uses A*, else false dijkstra is used


    # Choose which shortest-path function to use internally
    def _shortest_path(
        gd: GraphData, s: IATA, g: IATA,
        blk: Set[IATA], alw: Optional[Set[str]],
        mh: int, be: Optional[Set[Tuple[IATA, IATA]]] = None
    ) -> Tuple[List[IATA], float]:
        if use_astar:
            return astar(gd, s, g, blk, alw, mh, be)
        else:
            return dijkstra(gd, s, g, w, blk, alw, mh, be)
    
    first_path, first_cost = _shortest_path(gd, start, goal, blocked, allowed, max_hops)
    if not first_path:
        return []
    
    A = [first_path]
    B: List[Tuple[float, Tuple[IATA, ...]]] = []

    for ki in range(1, k):
        last_path = A[-1]
        
        # We need the cost of the root_path to add to the spur_path cost
        # Pre-calculating root_cost incrementally as we move the spur node
        accumulated_root_cost = 0.0

        for i in range(len(last_path) - 1):
            spur_node = last_path[i]
            root_path = last_path[:i + 1]

            # 1. Update accumulated_root_cost for the current root_path
            if i > 0:
                prev_node = last_path[i-1]
                edge = gd.edge_lookup[prev_node][spur_node]
                if use_astar:
                    accumulated_root_cost += edge.km
                else:
                    accumulated_root_cost += float(w(edge))

            # 2. Identify edges to block
            blocked_edges: Set[Tuple[IATA, IATA]] = set()
            for p in A:
                if len(p) > i and p[:i + 1] == root_path:
                    blocked_edges.add((p[i], p[i + 1]))

            # 3. Get the spur path AND its cost directly from Dijkstra
            temp_blocked = set(blocked)
            temp_blocked.update(root_path[:-1])
            
            spur_path, spur_cost = _shortest_path(
                gd, spur_node, goal, temp_blocked, allowed,
                max_hops, blocked_edges
            )
            
            if spur_path and spur_cost != float('inf'):
                total_cand_path = root_path[:-1] + spur_path
                total_cand_cost = accumulated_root_cost + spur_cost
                
                if (len(total_cand_path) - 1) <= max_hops:
                    heapq.heappush(B, (total_cand_cost, tuple(total_cand_path)))

        if not B:
            break

        # Move the best candidate from B to A, ensuring it's not a duplicate
        while B:
            cost, cand = heapq.heappop(B)
            cand_list = list(cand)
            if cand_list not in A:
                A.append(cand_list)
                break
        else:
            break

    return A