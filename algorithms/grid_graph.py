"""
grid_graph.py - Turns the vault map into a GRAPH that the searches can walk.

From a grid to a graph
----------------------
    * every walkable tile is a NODE                  e.g. (3, 8)
    * two nodes are joined by an EDGE when the tiles touch
      (up, down, left or right; no diagonal moves, same as the game)

The graph is stored as an ADJACENCY LIST: a dictionary that maps every node
to the list of its neighbours.

        . . #           (0,0): [(1,0), (0,1)]
        . # #     ->    (1,0): [(0,0)]
        . . .           (0,1): [(0,0), (0,2)]      ... and so on

Why an adjacency list and not an adjacency matrix?
    Our level has 300 walkable tiles.  A matrix would need 300 x 300 = 90,000
    cells, and almost all of them would say "not connected", because a tile
    has at most 4 neighbours.  The list stores only the real edges, so it
    uses O(V + E) memory instead of O(V^2).

Edge costs (a weighted graph)
-----------------------------
By default every step costs 1, so the cheapest path is simply the shortest.
You can pass an 'extra_cost' function to make some tiles more expensive to
step onto (for example, tiles that a camera can see).  Greedy and A* use
these costs; BFS and DFS ignore them, because they only count steps.
"""

# The order we look at neighbours in: up, right, down, left (clockwise).
# A fixed order makes every search give the same answer every time we run it.
NEIGHBOUR_OFFSETS = ((0, -1), (1, 0), (0, 1), (-1, 0))


class GridGraph:
    """
    The vault as a graph, built once from the current map.

        graph = GridGraph(vault)
        graph.neighbours((3, 8))       -> [(3, 7), (4, 8), (3, 9), (2, 8)]
        graph.cost((3, 8), (4, 8))     -> 1.0

    The graph is a SNAPSHOT of the map.  If the map changes (a door gets
    unlocked), build a new GridGraph.  Building one takes well under a
    millisecond on our 28 x 16 level, so this is cheap.
    """

    def __init__(self, vault, through_locked_doors=False, extra_cost=None):
        """
        vault                 environment.vault.Vault
        through_locked_doors  treat locked doors as walkable (used when we
                              plan "as if we already had the key")
        extra_cost            optional function tile -> number, added to the
                              cost of stepping ONTO that tile (must be >= 0)
        """
        self.width = vault.width
        self.height = vault.height
        self.through_locked_doors = through_locked_doors
        self._extra_cost = extra_cost
        self._adjacency = self._build_adjacency(vault)

    # ------------------------------------------------------------------
    # Building the adjacency list
    # ------------------------------------------------------------------
    def _is_passable(self, vault, x, y):
        """Can a character stand on tile (x, y) in this graph?"""
        if vault.is_walkable(x, y):
            return True
        return self.through_locked_doors and vault.is_locked_door(x, y)

    def _build_adjacency(self, vault):
        """Visit every tile once and record its passable neighbours.  O(V)."""
        adjacency = {}
        for y in range(vault.height):
            for x in range(vault.width):
                if not self._is_passable(vault, x, y):
                    continue
                neighbours = []
                for dx, dy in NEIGHBOUR_OFFSETS:
                    nx, ny = x + dx, y + dy
                    if vault.in_bounds(nx, ny) and self._is_passable(vault, nx, ny):
                        neighbours.append((nx, ny))
                adjacency[(x, y)] = neighbours
        return adjacency

    # ------------------------------------------------------------------
    # Questions the search algorithms ask
    # ------------------------------------------------------------------
    def neighbours(self, tile):
        """The tiles you can step to from 'tile'.  O(1) dictionary lookup."""
        return self._adjacency.get(tile, [])

    def cost(self, from_tile, to_tile):
        """Cost of one step from 'from_tile' onto the neighbouring 'to_tile'."""
        if self._extra_cost is None:
            return 1.0
        return 1.0 + self._extra_cost(to_tile)

    def path_cost(self, path):
        """Total cost of walking a whole path (0 for a one-tile path)."""
        if not path:
            return 0.0
        return sum(self.cost(path[i], path[i + 1]) for i in range(len(path) - 1))

    @property
    def nodes(self):
        """Every walkable tile."""
        return list(self._adjacency)

    def edge_count(self):
        """Number of connections.  Each one is listed twice (A->B and B->A)."""
        return sum(len(n) for n in self._adjacency.values()) // 2

    def __contains__(self, tile):
        """Lets you write: if tile in graph: ..."""
        return tile in self._adjacency

    def __len__(self):
        """Number of nodes, so len(graph) works."""
        return len(self._adjacency)

    def __repr__(self):
        return "GridGraph(nodes=" + str(len(self)) + ", edges=" + str(self.edge_count()) + ")"
