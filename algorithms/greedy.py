"""
greedy.py - Greedy Best-First Search   *** PLACEHOLDER - NOT IMPLEMENTED YET ***

Planned uses
------------
* Fast, heuristic-based pathfinding. It always expands the tile that
  *looks* closest to the goal (smallest h), ignoring the cost so far.

Interface: same as bfs.py
    find_path(vault, start, goal) -> list of (x, y) tiles, or None

Hints
-----
* h can be the Manhattan distance: abs(x1 - x2) + abs(y1 - y2).
  (environment.security.manhattan_distance already does this.)
* You need a priority queue. Python's heapq module provides one.
* Think about when greedy search finds a path that is NOT the shortest.
"""


def find_path(vault, start, goal):
    """TODO: implement Greedy Best-First Search."""
    raise NotImplementedError("Greedy Best-First Search has not been implemented yet.")
