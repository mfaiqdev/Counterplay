"""
bfs.py - Breadth-First Search.

The idea
--------
BFS explores the map in RINGS, like ripples spreading out when you drop a
stone in water: first every tile 1 step away from the start, then every tile
2 steps away, then 3, and so on.  It does this with a QUEUE (first in, first
out): tiles found earlier are expanded earlier.

Because the rings grow one step at a time, the FIRST time BFS reaches the
goal it has found a path with the fewest possible steps.  So on our grid,
where every step counts the same, BFS always returns a shortest path.

Planned uses in Counterplay
---------------------------
* Guards chasing the thief (they finally walk AROUND walls).
* Checking that a level can be completed (key, vault, loot, exit reachable).
* The baseline in the algorithm comparison: every other search is judged
  against BFS's shortest path length.

Complexity (V = tiles, E = connections between tiles)
-----------------------------------------------------
    time   O(V + E)   every tile is enqueued at most once and every
                      connection is looked at at most twice
    space  O(V)       the queue and the came_from dictionary

Interface (shared by bfs.py, dfs.py, greedy.py and astar.py)
------------------------------------------------------------
    find_path(vault, start, goal) -> list of (x, y) tiles, or None
    search(graph, start, goal)    -> generator of SearchStep snapshots
"""

from algorithms.data_structures import Queue
from algorithms.grid_graph import GridGraph
from algorithms.search_core import (
    SearchStep, endpoints_are_valid, reconstruct_path, run_search,
)

NAME = "BFS"


def search(graph, start, goal):
    """
    Breadth-First Search as a pausable generator.

    Yields one SearchStep after expanding each tile.  The last SearchStep
    has finished=True and holds the path (or None if there is no path).
    """
    came_from = {start: None}         # every DISCOVERED tile -> where we came from
    frontier = Queue([start])         # tiles discovered but not yet expanded
    nodes_expanded = 0

    if not endpoints_are_valid(graph, start, goal):
        yield SearchStep(None, frontier, came_from, nodes_expanded, finished=True)
        return

    while frontier:
        current = frontier.dequeue()              # the OLDEST waiting tile
        nodes_expanded += 1

        if current == goal:
            path = reconstruct_path(came_from, goal)
            yield SearchStep(current, frontier, came_from, nodes_expanded,
                             finished=True, path=path)
            return

        for neighbour in graph.neighbours(current):
            # Mark a tile as discovered the moment it joins the queue, so the
            # same tile can never be in the queue twice.
            if neighbour not in came_from:
                came_from[neighbour] = current
                frontier.enqueue(neighbour)

        yield SearchStep(current, frontier, came_from, nodes_expanded)

    # The queue ran out before we reached the goal: no path exists.
    yield SearchStep(None, frontier, came_from, nodes_expanded, finished=True)


def find_path(vault, start, goal, through_locked_doors=False):
    """
    Shortest path (fewest steps) from start to goal.

    Returns the list of tiles from start to goal (both included), or None
    if the goal cannot be reached.  Locked doors count as walls unless
    through_locked_doors is True.
    """
    graph = GridGraph(vault, through_locked_doors=through_locked_doors)
    return run_search(NAME, search(graph, start, goal), graph).path
