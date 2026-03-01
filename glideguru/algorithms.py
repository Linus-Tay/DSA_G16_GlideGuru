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

def dijkstra(
    gd: GraphData, start: IATA, goal: IATA, w: Callable[[Edge], float],
    blocked: Set[IATA], allowed: Optional[Set[str]], max_hops: int,
    blocked_edges: Optional[Set[Tuple[IATA, IATA]]] = None
) -> Tuple[List[IATA], float]:
    if start in blocked or goal in blocked: return [], float("inf")
    blocked_edges = blocked_edges or set()
    dist: Dict[IATA, float] = {start: 0.0}
    prev: Dict[IATA, Optional[IATA]] = {start: None}
    hops: Dict[IATA, int] = {start: 0}
    pq: List[Tuple[float, IATA]] = [(0.0, start)]
    while pq:
        cost, u = heapq.heappop(pq)
        if cost != dist.get(u, float("inf")): continue
        if u == goal: break
        for e in gd.graph.get(u, []):
            v = e.dest
            if v in blocked or (u, v) in blocked_edges: continue
            real = gd.edge_lookup[u].get(v)
            if not real or not _allows(real, allowed): continue
            nh = hops[u] + 1
            if nh > max_hops: continue
            nc = cost + float(w(real))
            if nc < dist.get(v, float("inf")):
                dist[v] = nc; prev[v] = u; hops[v] = nh
                heapq.heappush(pq, (nc, v))
    if goal not in prev: return [], float("inf")
    path: List[IATA] = []
    cur: Optional[IATA] = goal
    while cur is not None:
        path.append(cur); cur = prev[cur]
    path.reverse()
    return path, dist.get(goal, float("inf"))

def yen_k_paths(
    gd: GraphData, start: IATA, goal: IATA, w: Callable[[Edge], float], k: int,
    blocked: Set[IATA], allowed: Optional[Set[str]], max_hops: int
) -> List[List[IATA]]:
    first, _ = dijkstra(gd, start, goal, w, blocked, allowed, max_hops=max_hops)
    if not first: return []

    def cost(p: List[IATA]) -> float:
        return sum(float(w(gd.edge_lookup[p[i]][p[i + 1]])) for i in range(len(p) - 1))

    A = [first]
    B: List[Tuple[float, Tuple[IATA, ...]]] = []
    for _ in range(1, k):
        last = A[-1]
        for i in range(len(last) - 1):
            spur = last[i]
            root = last[: i + 1]
            blocked_edges: Set[Tuple[IATA, IATA]] = set()
            for p in A:
                if len(p) > i and p[: i + 1] == root:
                    blocked_edges.add((p[i], p[i + 1]))
            temp_blocked = set(blocked); temp_blocked.update(root[:-1])
            spur_path, _ = dijkstra(gd, spur, goal, w, temp_blocked, allowed, max_hops=max_hops, blocked_edges=blocked_edges)
            if not spur_path: continue
            cand = root[:-1] + spur_path
            if (len(cand) - 1) <= max_hops:
                heapq.heappush(B, (cost(cand), tuple(cand)))
        if not B: break
        while B:
            _, cand = heapq.heappop(B)
            cand_list = list(cand)
            if cand_list not in A:
                A.append(cand_list)
                break
        else:
            break
    return A