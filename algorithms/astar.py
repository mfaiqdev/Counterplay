"""
astar.py - A* Search.

The idea
--------
A* combines what BFS and Greedy are each good at.  Every tile gets three
numbers:

    g = the real cost of the best path found so far from the start to here
    h = the heuristic: an estimate of the cost from here to the goal
    f = g + h = the estimated cost of the WHOLE trip through this tile

A* keeps the waiting tiles in OUR MinHeap ordered by f, and always expands
the tile with the smallest f.  g keeps it honest (no rushing into dead ends
like Greedy) and h aims it at the goal (no exploring in every direction like
BFS).

Why A* finds the cheapest path
------------------------------
If h never OVERESTIMATES the real remaining cost ("admissible"), A* is
guaranteed to return a cheapest path.  Manhattan distance is admissible
here: every step costs at least 1 and a path can never be shorter than the
Manhattan distance.  It is even "consistent" (h drops by at most 1 per step),
which means the first time A* expands a tile, it has already found the best
way to reach it.

Weighted paths
--------------
A* uses the graph's step costs, so if a GridGraph is built with extra_cost
(for example, extra cost for tiles a camera can see), A* returns the path
with the lowest TOTAL cost: short AND safe.  The extra cost is never
negative, so Manhattan stays admissible.  This is where the learned risk
model will plug in.

Updating a tile's priority ("lazy deletion")
--------------------------------------------
Sometimes A* finds a cheaper way to a tile that is already waiting in the
heap.  A heap cannot easily change an item's priority, so we simply push the
tile again with the better f.  The old copy is still in the heap; when it
comes out later, the tile is already in 'expanded', so we skip it.

Complexity (V = tiles, E = connections between tiles)
-----------------------------------------------------
    time   O(E log V) in the worst case, the same as Dijkstra's algorithm;
           in practice a good h makes A* expand far fewer tiles
    space  O(V + E)   the heap can hold old copies (lazy deletion)
"""

from itertools import count

from algorithms.data_structures import MinHeap
from algorithms.grid_graph import GridGraph
from algorithms.search_core import (
    SearchStep, endpoints_are_valid, manhattan, reconstruct_path, run_search,
)

NAME = "A*"


def search(graph, start, goal, heuristic=manhattan):
    """
    A* Search as a pausable generator.

    heuristic   function (tile, goal) -> estimated remaining cost.  It must
                never overestimate, or the path may not be the cheapest.

    Heap entries are (f, h, order, tile).  On a tie in f, the tile with the
    smaller h (closer to the goal) comes out first, which saves work; 'order'
    settles any remaining tie so every run behaves the same way.
    """
    order = count()
    h_start = heuristic(start, goal)
    came_from = {start: None}
    cost_so_far = {start: 0.0}                    # g for every discovered tile
    expanded = set()
    frontier = MinHeap([(h_start, h_start, next(order), start)])
    nodes_expanded = 0

    if not endpoints_are_valid(graph, start, goal):
        yield SearchStep(None, frontier, came_from, nodes_expanded,
                         finished=True, cost_so_far=cost_so_far)
        return

    while frontier:
        _f, _h, _order, current = frontier.pop()  # the smallest f = g + h
        if current in expanded:
            continue                              # an old copy (lazy deletion)
        expanded.add(current)
        nodes_expanded += 1

        if current == goal:
            path = reconstruct_path(came_from, goal)
            yield SearchStep(current, frontier, came_from, nodes_expanded,
                             finished=True, path=path, cost_so_far=cost_so_far)
            return

        for neighbour in graph.neighbours(current):
            new_g = cost_so_far[current] + graph.cost(current, neighbour)
            # A new tile, or a CHEAPER way to a tile we already knew about?
            if neighbour not in cost_so_far or new_g < cost_so_far[neighbour]:
                cost_so_far[neighbour] = new_g
                came_from[neighbour] = current
                h = heuristic(neighbour, goal)
                frontier.push((new_g + h, h, next(order), neighbour))

        yield SearchStep(current, frontier, came_from, nodes_expanded,
                         cost_so_far=cost_so_far)

    yield SearchStep(None, frontier, came_from, nodes_expanded,
                     finished=True, cost_so_far=cost_so_far)


def find_path(vault, start, goal, through_locked_doors=False, extra_cost=None):
    """
    Cheapest path from start to goal.

    With the default costs (every step = 1) this is a shortest path, the same
    length BFS finds, usually after expanding far fewer tiles.
    extra_cost   optional function tile -> extra cost for stepping onto it
    Returns the list of tiles from start to goal (both included), or None.
    """
    graph = GridGraph(vault, through_locked_doors=through_locked_doors,
                      extra_cost=extra_cost)
    return run_search(NAME, search(graph, start, goal), graph).path
