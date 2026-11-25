"""
dfs.py - Depth-First Search.

The idea
--------
DFS is how you would explore a maze on your own: keep walking down one
corridor as far as it goes, and only when you hit a dead end, BACKTRACK to
the last place where you had another choice.  It does this with a STACK
(last in, first out): the tile found most recently is expanded next.

DFS finds A path, but usually NOT the shortest one, because it commits to
the first direction it tries instead of looking around evenly like BFS.
That difference is exactly what our comparison will show.

Two versions are in this file
-----------------------------
* search(...) / find_path(...)   iterative, with OUR Stack. Used by the game.
* find_path_recursive(...)       the classic recursive version, for comparison.

They explore in the same order.  The recursive one uses Python's CALL STACK
instead of our Stack: every recursive call is pushed on it, and returning
from a call pops it, which is the "backtracking".  Python stops a program
after about 1000 nested calls (the recursion limit), so on big maps the
iterative version is the safe one.  Our level has only 300 tiles, so both
work here.

Complexity (V = tiles, E = connections between tiles)
-----------------------------------------------------
    time   O(V + E)   every tile is expanded at most once
    space  O(V + E)   a tile can sit on the stack once per neighbour that
                      pushed it (on a grid E <= 2V, so this is still O(V))
"""

from algorithms.data_structures import Stack
from algorithms.grid_graph import GridGraph
from algorithms.search_core import (
    SearchStep, endpoints_are_valid, reconstruct_path, run_search,
)

NAME = "DFS"


def search(graph, start, goal):
    """
    Depth-First Search as a pausable generator.

    Yields one SearchStep after expanding each tile.  The last SearchStep
    has finished=True and holds the path (or None if there is no path).
    """
    came_from = {start: None}         # tile -> the tile that most recently pushed it
    expanded = set()                  # tiles we have already explored from
    frontier = Stack([start])
    nodes_expanded = 0

    if not endpoints_are_valid(graph, start, goal):
        yield SearchStep(None, frontier, came_from, nodes_expanded, finished=True)
        return

    while frontier:
        current = frontier.pop()                  # the NEWEST tile
        if current in expanded:
            continue                              # an old copy: already explored
        expanded.add(current)
        nodes_expanded += 1

        if current == goal:
            path = reconstruct_path(came_from, goal)
            yield SearchStep(current, frontier, came_from, nodes_expanded,
                             finished=True, path=path)
            return

        # Push in REVERSE order, so the first neighbour (up) ends on top of
        # the stack and is explored first.
        for neighbour in reversed(graph.neighbours(current)):
            if neighbour not in expanded:
                came_from[neighbour] = current    # the latest push wins
                frontier.push(neighbour)

        yield SearchStep(current, frontier, came_from, nodes_expanded)

    yield SearchStep(None, frontier, came_from, nodes_expanded, finished=True)


def find_path(vault, start, goal, through_locked_doors=False):
    """
    A path from start to goal found by DFS (valid, but often not the shortest).

    Returns the list of tiles from start to goal (both included), or None.
    """
    graph = GridGraph(vault, through_locked_doors=through_locked_doors)
    return run_search(NAME, search(graph, start, goal), graph).path


def find_path_recursive(vault, start, goal, through_locked_doors=False):
    """
    The same search written recursively, the way DFS is usually taught.

    'path' is the corridor we are currently standing in.  We step forward
    with path.append(...) and BACKTRACK with path.pop() when a direction
    leads nowhere.
    """
    graph = GridGraph(vault, through_locked_doors=through_locked_doors)
    if not endpoints_are_valid(graph, start, goal):
        return None

    visited = set()
    path = []

    def explore(tile):
        visited.add(tile)
        path.append(tile)                         # step forward
        if tile == goal:
            return True
        for neighbour in graph.neighbours(tile):
            if neighbour not in visited and explore(neighbour):
                return True
        path.pop()                                # dead end: backtrack
        return False

    return list(path) if explore(start) else None
