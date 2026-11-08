"""
astar.py - A* Search   *** PLACEHOLDER - NOT IMPLEMENTED YET ***

Planned uses
------------
* Optimal pathfinding for the thief and for guards chasing the thief.
* Replanning when doors, guards or the alert level change.

Interface: same as bfs.py
    find_path(vault, start, goal) -> list of (x, y) tiles, or None

Hints
-----
* Every tile gets three numbers:
      g = cost of the path from start to this tile
      h = heuristic estimate from this tile to the goal
      f = g + h        (the priority queue is ordered by f)
* Use heapq as the priority queue.
* Later you can add extra cost to tiles that guards or cameras can see,
  so the thief prefers hidden routes.
"""


def find_path(vault, start, goal):
    """TODO: implement A* Search."""
    raise NotImplementedError("A* has not been implemented yet.")
