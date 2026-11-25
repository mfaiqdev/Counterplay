"""
greedy.py - Greedy Best-First Search.

The idea
--------
Greedy always expands the tile that LOOKS closest to the goal, measured by a
heuristic h (we use the Manhattan distance).  It never looks at how far it
has already walked.  It keeps the waiting tiles in OUR MinHeap, ordered by h,
so the most promising tile is always on top.

    BFS     asks: "which tile is closest to the START?"   (explores evenly)
    Greedy  asks: "which tile LOOKS closest to the GOAL?" (rushes at the goal)
    A*      asks both: "smallest g + h"                   (see astar.py)

Greedy is usually very fast because it heads straight for the goal.  But it
is NOT guaranteed to find the shortest path: if a wall blocks the straight
line, it can walk deep into a dead end before it turns around, and the path
it returns can be longer than necessary.

Note: the priority is h ONLY.  If you order by g + h you get A*, not Greedy.

Complexity (V = tiles, E = connections between tiles)
-----------------------------------------------------
    time   O(E log V)   each discovered tile is pushed once, and every heap
                        push or pop costs O(log V)
    space  O(V)         the heap, came_from and cost_so_far
"""

from itertools import count

from algorithms.data_structures import MinHeap
from algorithms.grid_graph import GridGraph
from algorithms.search_core import (
    SearchStep, endpoints_are_valid, manhattan, reconstruct_path, run_search,
)

NAME = "Greedy"


def search(graph, start, goal, heuristic=manhattan):
    """
    Greedy Best-First Search as a pausable generator.

    heuristic   function (tile, goal) -> estimated distance, Manhattan by default

    Heap entries are (h, order, tile).  'order' is a running number: when two
    tiles have the same h, the one discovered first comes out first, so the
    search behaves the same way every run.
    """
    order = count()                                # 0, 1, 2, 3, ...
    came_from = {start: None}
    cost_so_far = {start: 0.0}                     # g: not used to choose, only reported
    frontier = MinHeap([(heuristic(start, goal), next(order), start)])
    nodes_expanded = 0

    if not endpoints_are_valid(graph, start, goal):
        yield SearchStep(None, frontier, came_from, nodes_expanded,
                         finished=True, cost_so_far=cost_so_far)
        return

    while frontier:
        _h, _order, current = frontier.pop()       # the tile that LOOKS closest
        nodes_expanded += 1

        if current == goal:
            path = reconstruct_path(came_from, goal)
            yield SearchStep(current, frontier, came_from, nodes_expanded,
                             finished=True, path=path, cost_so_far=cost_so_far)
            return

        for neighbour in graph.neighbours(current):
            if neighbour not in came_from:          # discovered for the first time
                came_from[neighbour] = current
                cost_so_far[neighbour] = cost_so_far[current] + graph.cost(current, neighbour)
                frontier.push((heuristic(neighbour, goal), next(order), neighbour))

        yield SearchStep(current, frontier, came_from, nodes_expanded,
                         cost_so_far=cost_so_far)

    yield SearchStep(None, frontier, came_from, nodes_expanded,
                     finished=True, cost_so_far=cost_so_far)


def find_path(vault, start, goal, through_locked_doors=False):
    """
    A path from start to goal found by Greedy Best-First Search.

    Fast, but not always the shortest.  Returns a list of tiles or None.
    """
    graph = GridGraph(vault, through_locked_doors=through_locked_doors)
    return run_search(NAME, search(graph, start, goal), graph).path
