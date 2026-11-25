"""
algorithms package - our DSA search algorithms.

    bfs.py      Breadth-First Search       Queue           fewest steps, explores evenly
    dfs.py      Depth-First Search         Stack           a path, usually not the shortest
    greedy.py   Greedy Best-First Search   MinHeap by h    very fast, not always shortest
    astar.py    A* Search                  MinHeap by g+h  cheapest path, little wasted work

Shared building blocks:
    data_structures.py   our own Queue, Stack and MinHeap
    grid_graph.py        the vault map as an adjacency-list graph
    search_core.py       heuristic, path rebuilding, SearchStep, SearchResult

Every algorithm module offers the same interface, so the game can swap one
for another:

    NAME                              display name, e.g. "A*"
    find_path(vault, start, goal)     list of (x, y) tiles from start to goal, or None
    search(graph, start, goal)        generator of SearchStep snapshots (for visualizing)

To use every algorithm, for example in a comparison:

    from algorithms import ALGORITHMS
    for algorithm in ALGORITHMS:
        print(algorithm.NAME, algorithm.find_path(vault, start, goal))

To pick one by its short name ("bfs", "dfs", "greedy", "astar"):

    from algorithms import BY_KEY
    search = BY_KEY["astar"]
"""

from algorithms import astar, bfs, dfs, greedy

ALGORITHMS = (bfs, dfs, greedy, astar)

# "bfs" -> bfs module, "astar" -> astar module, ... (the file name without .py)
BY_KEY = {module.__name__.split(".")[-1]: module for module in ALGORITHMS}
