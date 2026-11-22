"""
Tests for the search algorithms in algorithms/ (BFS for now; DFS, Greedy and
A* join this file as they are written).

Run from the project folder with:
    python -m unittest discover -s tests -v

How we know a search is correct
-------------------------------
1. Hand-checked cases on a tiny map (drawn below), plus edge cases: start
   equals goal, goal inside a wall, goal behind the locked door.
2. Every returned path is checked step by step: it starts at the start, ends
   at the goal, only moves between neighbouring walkable tiles, and never
   visits a tile twice.
3. An "oracle" test: a separate, very simple BFS written with Python's own
   deque (in this file) computes the true shortest distance for hundreds of
   random start/goal pairs on the real level.  Our BFS must agree every time.

The tiny map:
        x: 0 1 2 3 4
    y=0    # # # # #
    y=1    # . . . #
    y=2    # . # . #
    y=3    # . D . #        D = locked door at (2, 3)
    y=4    # # # # #
"""

import os
import random
import sys
import unittest
from collections import deque

# Make "algorithms" and "environment" importable from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment.vault import Vault, ITEM_KEY, ITEM_GOLD
from algorithms import bfs
from algorithms.grid_graph import GridGraph
from algorithms.search_core import run_search

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
    for position, item in vault.items.items():
        if item == kind:
            return position
    return None


def reference_distance(graph, start, goal):
    """
    The 'oracle': true number of steps from start to goal, or None.
    Written as simply as possible with Python's deque, completely separately
    from our own code, so the two can check each other.
    """
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


class PathChecks(unittest.TestCase):
    """Shared checks used by the test classes of every algorithm."""

    def assertValidPath(self, graph, path, start, goal):
        self.assertIsNotNone(path, "expected a path but got None")
        self.assertEqual(path[0], start, "path must begin at the start")
        self.assertEqual(path[-1], goal, "path must end at the goal")
        self.assertEqual(len(path), len(set(path)), "path visits a tile twice")
        for here, there in zip(path, path[1:]):
            self.assertIn(there, graph.neighbours(here),
                          "illegal move " + str(here) + " -> " + str(there))


class TestBFS(PathChecks):
    # ---------------- hand-checked cases on the tiny map ----------------
    def test_finds_the_only_route_around_the_locked_door(self):
        path = bfs.find_path(tiny_vault(), (1, 1), (3, 3))
        self.assertEqual(path, [(1, 1), (2, 1), (3, 1), (3, 2), (3, 3)])

    def test_start_equal_to_goal_is_a_one_tile_path(self):
        self.assertEqual(bfs.find_path(tiny_vault(), (1, 1), (1, 1)), [(1, 1)])

    def test_goal_inside_a_wall_has_no_path(self):
        self.assertIsNone(bfs.find_path(tiny_vault(), (1, 1), (2, 2)))

    def test_start_outside_the_map_has_no_path(self):
        self.assertIsNone(bfs.find_path(tiny_vault(), (-1, -1), (1, 1)))

    def test_locked_door_is_a_wall_unless_allowed(self):
        self.assertIsNone(bfs.find_path(tiny_vault(), (1, 1), (2, 3)))
        path = bfs.find_path(tiny_vault(), (1, 1), (2, 3), through_locked_doors=True)
        self.assertEqual(path, [(1, 1), (1, 2), (1, 3), (2, 3)])

    # ---------------- the real level ----------------
    def test_thief_start_to_key_takes_15_steps(self):
        vault = Vault()
        path = bfs.find_path(vault, vault.start, find_item(vault, ITEM_KEY))
        self.assertValidPath(GridGraph(vault), path, vault.start, (2, 2))
        self.assertEqual(len(path) - 1, 15)

    def test_loot_is_unreachable_without_the_key(self):
        vault = Vault()
        gold = find_item(vault, ITEM_GOLD)
        self.assertIsNone(bfs.find_path(vault, vault.start, gold))
        path = bfs.find_path(vault, vault.start, gold, through_locked_doors=True)
        self.assertValidPath(GridGraph(vault, through_locked_doors=True),
                             path, vault.start, gold)

    def test_agrees_with_the_oracle_on_random_pairs(self):
        vault = Vault()
        graph = GridGraph(vault)
        tiles = sorted(graph.nodes)
        rng = random.Random(2026)                     # same pairs on every run
        for _ in range(300):
            start, goal = rng.choice(tiles), rng.choice(tiles)
            path = bfs.find_path(vault, start, goal)
            expected = reference_distance(graph, start, goal)
            if expected is None:
                self.assertIsNone(path, (start, goal))
            else:
                self.assertValidPath(graph, path, start, goal)
                self.assertEqual(len(path) - 1, expected, (start, goal))

    # ---------------- the pausable search ----------------
    def test_search_yields_one_step_per_expanded_tile(self):
        graph = GridGraph(Vault())
        steps = list(bfs.search(graph, (2, 13), (2, 2)))
        self.assertTrue(steps[-1].finished)
        self.assertTrue(all(not s.finished for s in steps[:-1]))
        self.assertEqual([s.nodes_expanded for s in steps], list(range(1, len(steps) + 1)))

    def test_rings_grow_outward(self):
        """BFS expands every tile at distance d before any tile at distance d + 1."""
        graph = GridGraph(Vault())
        start = (2, 13)
        distances = [reference_distance(graph, start, step.current)
                     for step in bfs.search(graph, start, (26, 14)) if step.current]
        self.assertEqual(distances, sorted(distances))

    def test_run_search_reports_statistics(self):
        graph = GridGraph(Vault())
        result = run_search("BFS", bfs.search(graph, (2, 13), (2, 2)), graph)
        self.assertTrue(result.found)
        self.assertEqual(result.steps, 15)
        self.assertEqual(result.path_cost, 15.0)
        self.assertGreater(result.nodes_expanded, 15)        # it explored more than the path
        self.assertLessEqual(result.nodes_expanded, len(graph))
        self.assertGreaterEqual(result.nodes_discovered, result.nodes_expanded)


if __name__ == "__main__":
    unittest.main()
