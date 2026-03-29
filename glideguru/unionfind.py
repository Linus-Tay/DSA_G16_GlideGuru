class UnionFind:
    def __init__(self, nodes):
        self.parent = {n: n for n in nodes}
        self.rank = {n: 0 for n in nodes}

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a, b):
        pa = self.find(a)
        pb = self.find(b)

        if pa == pb:
            return

        if self.rank[pa] < self.rank[pb]:
            self.parent[pa] = pb
        elif self.rank[pa] > self.rank[pb]:
            self.parent[pb] = pa
        else:
            self.parent[pb] = pa
            self.rank[pa] += 1