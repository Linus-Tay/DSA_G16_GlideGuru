import heapq
from collections import deque
from typing import Callable, Dict, List, Optional, Set, Tuple
from glideguru.data import Edge, GraphData, IATA

def _allows(edge: Edge, allowed: Optional[Set[str]]) -> bool:
    return (not allowed) or any(c.iata in allowed for c in edge.carriers)

def bfs_hops(gd: GraphData, start: IATA, goal: IATA, blocked: Set[IATA], allowed: Optional[Set[str]], max_hops: int) -> List[IATA]:
    if start in blocked or goal in blocked: return []
    q = deque([start])
    prev: Dict[IATA, Optional[IATA]] = {start: None}
    depth: Dict[IATA, int] = {start: 0}
    while q:
        u = q.popleft()
        if u == goal: break
        for e in gd.graph.get(u, []):
            v = e.dest
            if v in blocked or v in prev: continue
            real = gd.edge_lookup[u].get(v)
            if not real or not _allows(real, allowed): continue
            d = depth[u] + 1
            if d > max_hops: continue
            prev[v] = u; depth[v] = d; q.append(v)
    if goal not in prev: return []
    path: List[IATA] = []
    cur: Optional[IATA] = goal
    while cur is not None:
        path.append(cur); cur = prev[cur]
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

def yen_k_paths(
    gd: GraphData, start: IATA, goal: IATA, w: Callable[[Edge], float], k: int,
    blocked: Set[IATA], allowed: Optional[Set[str]], max_hops: int
) -> List[List[IATA]]:
    # Get the initial shortest path and its cost
    first_path, first_cost = dijkstra(gd, start, goal, w, blocked, allowed, max_hops=max_hops)
    if not first_path: return []

    A = [first_path]
    # Store candidates as (total_cost, path_tuple) in the priority queue
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
                accumulated_root_cost += float(w(edge))

            # 2. Identify edges to block
            blocked_edges: Set[Tuple[IATA, IATA]] = set()
            for p in A:
                if len(p) > i and p[:i + 1] == root_path:
                    blocked_edges.add((p[i], p[i + 1]))

            # 3. Get the spur path AND its cost directly from Dijkstra
            temp_blocked = set(blocked)
            temp_blocked.update(root_path[:-1])
            
            spur_path, spur_cost = dijkstra(
                gd, spur_node, goal, w, temp_blocked, allowed, 
                max_hops=max_hops, blocked_edges=blocked_edges
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