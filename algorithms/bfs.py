"""
bfs.py - Breadth-First Search   *** PLACEHOLDER - NOT IMPLEMENTED YET ***

Planned uses
------------
* Find the shortest path (fewest steps) between two tiles.
* Validate that the vault can be reached (is the level solvable?).

Shared interface (use the same one in dfs.py, greedy.py and astar.py)
---------------------------------------------------------------------
    find_path(vault, start, goal) -> list of (x, y) tiles, or None

* 'vault' is environment.vault.Vault. Useful methods:
      vault.is_walkable(x, y)   vault.in_bounds(x, y)
* 'start' and 'goal' are (x, y) tuples.
* Return the tiles from start to goal (including both), or None if
  no path exists.

Hints
-----
* A Python list (or collections.deque) can be the queue.
* Remember which tiles you have already visited.
* Remember where each tile came from so you can rebuild the path.
* Decide how to handle locked doors (vault.is_walkable says False for them).
"""


def find_path(vault, start, goal):
    """TODO: implement Breadth-First Search."""
    raise NotImplementedError("BFS has not been implemented yet.")
