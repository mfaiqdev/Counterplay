"""
Tests for Depth-First Search (algorithms/dfs.py).

Run from the project folder with:
    python -m unittest discover -s tests -v

What we check
-------------
* DFS always returns a VALID path when one exists, and None when none does.
* It is NOT always the shortest (on the real level it takes 23 steps to the
  key, where 15 is possible), which is the key difference from BFS.
* It really goes deep first: after expanding a tile, the next tile it
  expands is one of that tile's neighbours, whenever one is unexplored.
* The recursive version finds exactly the same paths as the iterative one.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.vault import Vault, ITEM_KEY
from algorithms import dfs
from algorithms.grid_graph import GridGraph
from search_helpers import (
    PathChecks, tiny_vault, find_item, reference_distance, random_pairs,
)


class TestDFS(PathChecks, unittest.TestCase):
    # ---------------- tiny map and edge cases ----------------
    def test_finds_a_path_on_the_tiny_map(self):
        path = dfs.find_path(tiny_vault(), (1, 1), (3, 3))
        self.assertValidPath(GridGraph(tiny_vault()), path, (1, 1), (3, 3))

    def test_start_equal_to_goal_is_a_one_tile_path(self):
        self.assertEqual(dfs.find_path(tiny_vault(), (1, 1), (1, 1)), [(1, 1)])

    def test_goal_inside_a_wall_has_no_path(self):
        self.assertIsNone(dfs.find_path(tiny_vault(), (1, 1), (2, 2)))

    def test_locked_door_is_a_wall_unless_allowed(self):
        self.assertIsNone(dfs.find_path(tiny_vault(), (1, 1), (2, 3)))
        path = dfs.find_path(tiny_vault(), (1, 1), (2, 3), through_locked_doors=True)
        self.assertValidPath(GridGraph(tiny_vault(), through_locked_doors=True),
                             path, (1, 1), (2, 3))

    # ---------------- the real level ----------------
    def test_finds_the_key_but_not_by_the_shortest_route(self):
        vault = Vault()
        key = find_item(vault, ITEM_KEY)
        path = dfs.find_path(vault, vault.start, key)
        self.assertValidPath(GridGraph(vault), path, vault.start, key)
        self.assertEqual(len(path) - 1, 23)                  # BFS needs only 15

    def test_finds_a_path_exactly_when_one_exists(self):
        vault = Vault()
        graph = GridGraph(vault)
        for start, goal in random_pairs(graph, 300, seed=2026):
            path = dfs.find_path(vault, start, goal)
            shortest = reference_distance(graph, start, goal)
            if shortest is None:
                self.assertIsNone(path, (start, goal))
            else:
                self.assertValidPath(graph, path, start, goal)
                self.assertGreaterEqual(len(path) - 1, shortest)   # never shorter than optimal

    # ---------------- how it explores ----------------
    def test_goes_deep_first(self):
        """After expanding a tile, DFS next expands one of its neighbours if it can."""
        graph = GridGraph(Vault())
        expanded = []
        for step in dfs.search(graph, (2, 13), (26, 14)):
            if step.current is None:
                continue
            if expanded:
                previous = expanded[-1]
                unexplored = [n for n in graph.neighbours(previous) if n not in expanded]
                if unexplored:
                    self.assertIn(step.current, unexplored)
            expanded.append(step.current)

    def test_each_tile_is_expanded_at_most_once(self):
        graph = GridGraph(Vault())
        tiles = [s.current for s in dfs.search(graph, (2, 13), (26, 14)) if s.current]
        self.assertEqual(len(tiles), len(set(tiles)))

    # ---------------- recursive version ----------------
    def test_recursive_version_finds_the_same_paths(self):
        vault = Vault()
        graph = GridGraph(vault)
        for start, goal in random_pairs(graph, 150, seed=7):
            self.assertEqual(dfs.find_path_recursive(vault, start, goal),
                             dfs.find_path(vault, start, goal), (start, goal))

    def test_recursive_version_edge_cases(self):
        self.assertEqual(dfs.find_path_recursive(tiny_vault(), (1, 1), (1, 1)), [(1, 1)])
        self.assertIsNone(dfs.find_path_recursive(tiny_vault(), (1, 1), (2, 2)))


if __name__ == "__main__":
    unittest.main()
