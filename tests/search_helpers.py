"""
search_helpers.py - Shared tools for the search algorithm tests.

This file is not a test file itself (its name does not start with "test_"),
so unittest does not run it.  The test files for BFS, DFS, Greedy and A*
import what they need from here instead of copying it.

    TINY_LAYOUT, tiny_vault()   a 5 x 5 map small enough to check by eye
    find_item(vault, kind)      where an item (key, gold, ...) is on the map
    reference_distance(...)     "oracle": true fewest steps, with Python's deque
    reference_cost(...)         "oracle": true cheapest cost, with Python's heapq
    random_pairs(...)           repeatable random (start, goal) pairs
    PathChecks                  assertValidPath() for any returned path

The two oracles are written separately and as simply as possible, using only
Python's built-ins, so that they can check our own code independently.

The tiny map:
        x: 0 1 2 3 4
    y=0    # # # # #
    y=1    # . . . #
    y=2    # . # . #
    y=3    # . D . #        D = locked door at (2, 3)
    y=4    # # # # #
"""

import heapq
import os
import random
import sys
from collections import deque

# Make "algorithms" and "environment" importable from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment.vault import Vault

TINY_LAYOUT = [
    "#####",
    "#...#",
    "#.#.#",
    "#.D.#",
    "#####",
]


def tiny_vault():
    return Vault(TINY_LAYOUT)


def find_item(vault, kind):
    """Position of the first item of this kind, or None."""
    for position, item in vault.items.items():
        if item == kind:
            return position
    return None


def reference_distance(graph, start, goal):
    """True number of steps from start to goal (plain BFS with deque), or None."""
    if start not in graph or goal not in graph:
        return None
    distance = {start: 0}
    queue = deque([start])
    while queue:
        tile = queue.popleft()
        if tile == goal:
            return distance[tile]
        for neighbour in graph.neighbours(tile):
            if neighbour not in distance:
                distance[neighbour] = distance[tile] + 1
                queue.append(neighbour)
    return None


def reference_cost(graph, start, goal):
    """True cheapest path cost (plain Dijkstra with heapq), or None."""
    if start not in graph or goal not in graph:
        return None
    best = {start: 0.0}
    heap = [(0.0, start)]
    while heap:
        cost, tile = heapq.heappop(heap)
        if tile == goal:
            return cost
        if cost > best[tile]:
            continue                      # an outdated entry
        for neighbour in graph.neighbours(tile):
            new_cost = cost + graph.cost(tile, neighbour)
            if new_cost < best.get(neighbour, float("inf")):
                best[neighbour] = new_cost
                heapq.heappush(heap, (new_cost, neighbour))
    return None


def random_pairs(graph, count, seed):
    """'count' random (start, goal) pairs of walkable tiles, the same every run."""
    rng = random.Random(seed)
    tiles = sorted(graph.nodes)
    return [(rng.choice(tiles), rng.choice(tiles)) for _ in range(count)]


class PathChecks:
    """
    Mixed into a unittest.TestCase to add assertValidPath().

    A valid path starts at the start, ends at the goal, never visits a tile
    twice, and every move goes to a neighbouring walkable tile.
    """

    def assertValidPath(self, graph, path, start, goal):
        self.assertIsNotNone(path, "expected a path but got None")
        self.assertEqual(path[0], start, "path must begin at the start")
        self.assertEqual(path[-1], goal, "path must end at the goal")
        self.assertEqual(len(path), len(set(path)), "path visits a tile twice")
        for here, there in zip(path, path[1:]):
            self.assertIn(there, graph.neighbours(here),
                          "illegal move " + str(here) + " -> " + str(there))
