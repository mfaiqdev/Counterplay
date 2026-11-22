"""
search_core.py - The pieces that every search algorithm shares.

    manhattan(a, b)           the heuristic h used by Greedy and A*
    reconstruct_path(...)     rebuilds the path from the "came_from" map
    SearchStep                a snapshot of a search that is still running
    SearchResult              the final answer, plus numbers for comparisons
    run_search(...)           runs a search to the end and builds the result

How our searches are written: "pausable" searches
-------------------------------------------------
Each algorithm (bfs.py, dfs.py, greedy.py, astar.py) is written as a Python
GENERATOR.  A generator is a function that uses 'yield' instead of 'return'.
Every time it reaches 'yield' it hands back a value and PAUSES, keeping all
of its variables, until someone asks for the next value.

Our searches yield one SearchStep each time they expand a tile.  So the same
algorithm can be used in two ways:

    * The game wants the answer immediately:
          result = run_search("BFS", bfs.search(graph, start, goal), graph)

    * The visualizer (GlassBrain) wants to watch it think, one step per frame:
          for step in bfs.search(graph, start, goal):
              draw(step)

The algorithm is written once and never copied.
"""

import time
from dataclasses import dataclass

from algorithms.data_structures import Stack


# ---------------------------------------------------------------------------
# Heuristic
# ---------------------------------------------------------------------------
def manhattan(a, b):
    """
    Distance in tiles when you can only move up, down, left or right.

    It never OVERESTIMATES the real number of steps (walls can only make the
    real path longer, never shorter).  A heuristic with this property is
    called "admissible", and it is what keeps A* optimal.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------------------------------------------------------------------------
# Rebuilding the path
# ---------------------------------------------------------------------------
def reconstruct_path(came_from, goal):
    """
    Rebuild the path start -> goal from the 'came_from' dictionary.

    came_from maps every discovered tile to the tile we reached it from, and
    the start maps to None.  Following those links from the goal gives the
    path BACKWARDS (goal -> start).  We push each tile onto a Stack and then
    pop them all: last in, first out turns the order around.

    Returns None if the goal was never reached.  O(length of the path).
    """
    if goal not in came_from:
        return None
    stack = Stack()
    tile = goal
    while tile is not None:
        stack.push(tile)
        tile = came_from[tile]
    path = []
    while stack:
        path.append(stack.pop())
    return path


def endpoints_are_valid(graph, start, goal):
    """A path can only exist if both ends are walkable tiles of the graph."""
    return start in graph and goal in graph


# ---------------------------------------------------------------------------
# Snapshots and results
# ---------------------------------------------------------------------------
@dataclass
class SearchStep:
    """
    A snapshot of a search right after it expanded one tile.

    'frontier' and 'came_from' are the search's LIVE structures, not copies
    (copying them on every step would be slow).  Read them or draw them, but
    never change them, and do not keep them after asking for the next step.
    """
    current: tuple | None          # the tile just expanded (None if there is none)
    frontier: object               # the Queue / Stack / MinHeap of tiles waiting
    came_from: dict                # tile -> previous tile, for every DISCOVERED tile
    nodes_expanded: int            # tiles expanded so far
    finished: bool = False         # True only on the very last step
    path: list | None = None       # set on the last step (None means "no path")
    cost_so_far: dict | None = None    # g values (Greedy and A* fill this in)


@dataclass
class SearchResult:
    """The final answer of one search, plus numbers to compare algorithms."""
    algorithm: str                 # e.g. "BFS"
    path: list | None              # tiles from start to goal, or None
    path_cost: float               # total cost of the path (infinity if none)
    nodes_expanded: int            # tiles taken out of the frontier
    nodes_discovered: int          # tiles ever added to the frontier
    max_frontier_size: int         # biggest the frontier got (memory used)
    time_ms: float                 # how long the search took

    @property
    def found(self):
        return self.path is not None

    @property
    def steps(self):
        """Number of moves in the path (one less than the number of tiles)."""
        return len(self.path) - 1 if self.path else 0


def run_search(algorithm, steps, graph):
    """
    Run a search generator until it finishes, and return a SearchResult.

    algorithm  a name to store in the result, e.g. "BFS"
    steps      the generator, e.g. bfs.search(graph, start, goal)
    graph      the GridGraph the search ran on (used for the path cost)
    """
    started = time.perf_counter()
    max_frontier = 0
    last = None
    for step in steps:
        max_frontier = max(max_frontier, len(step.frontier))
        last = step
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if last is None:                   # a generator that yielded nothing
        return SearchResult(algorithm, None, float("inf"), 0, 0, 0, elapsed_ms)

    return SearchResult(
        algorithm=algorithm,
        path=last.path,
        path_cost=graph.path_cost(last.path) if last.path else float("inf"),
        nodes_expanded=last.nodes_expanded,
        nodes_discovered=len(last.came_from),
        max_frontier_size=max_frontier,
        time_ms=elapsed_ms,
    )
