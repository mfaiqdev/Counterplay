"""
Tests for Greedy Best-First Search (algorithms/greedy.py).

Run from the project folder with:
    python -m unittest discover -s tests -v

What we check
-------------
* Greedy always returns a VALID path when one exists, and None when none does.
* It is fast: on the real level it expands 19 tiles to find the key, where
  BFS expands 116.
* It is NOT always the shortest: from the start to the gold (through the
  vault door) it takes 40 steps, where 32 is possible.
* With a heuristic of 0 it has no idea where the goal is, so it falls back
  to first-come-first-served and expands tiles in exactly BFS's order.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.vault import Vault, ITEM_KEY, ITEM_GOLD
from algorithms import bfs, greedy
from algorithms.grid_graph import GridGraph
from algorithms.search_core import run_search
from search_helpers import (
    PathChecks, tiny_vault, find_item, reference_distance, random_pairs,
)


class TestGreedy(PathChecks, unittest.TestCase):
    # ---------------- tiny map and edge cases ----------------
    def test_finds_the_route_on_the_tiny_map(self):
        path = greedy.find_path(tiny_vault(), (1, 1), (3, 3))
        self.assertEqual(path, [(1, 1), (2, 1), (3, 1), (3, 2), (3, 3)])

    def test_start_equal_to_goal_is_a_one_tile_path(self):
        self.assertEqual(greedy.find_path(tiny_vault(), (1, 1), (1, 1)), [(1, 1)])

    def test_goal_inside_a_wall_has_no_path(self):
        self.assertIsNone(greedy.find_path(tiny_vault(), (1, 1), (2, 2)))

    def test_locked_door_is_a_wall_unless_allowed(self):
        self.assertIsNone(greedy.find_path(tiny_vault(), (1, 1), (2, 3)))
        self.assertIsNotNone(greedy.find_path(tiny_vault(), (1, 1), (2, 3),
                                              through_locked_doors=True))

    # ---------------- the real level ----------------
    def test_is_fast_on_the_way_to_the_key(self):
        vault = Vault()
        graph = GridGraph(vault)
        key = find_item(vault, ITEM_KEY)
        result = run_search("Greedy", greedy.search(graph, vault.start, key), graph)
        self.assertValidPath(graph, result.path, vault.start, key)
        self.assertEqual(result.steps, 15)
        self.assertEqual(result.nodes_expanded, 19)                 # BFS: 116

    def test_is_not_always_the_shortest(self):
        vault = Vault()
        graph = GridGraph(vault, through_locked_doors=True)
        gold = find_item(vault, ITEM_GOLD)
        path = greedy.find_path(vault, vault.start, gold, through_locked_doors=True)
        self.assertValidPath(graph, path, vault.start, gold)
        self.assertEqual(len(path) - 1, 40)
        self.assertEqual(reference_distance(graph, vault.start, gold), 32)

    def test_finds_a_path_exactly_when_one_exists(self):
        vault = Vault()
        graph = GridGraph(vault)
        for start, goal in random_pairs(graph, 300, seed=2026):
            path = greedy.find_path(vault, start, goal)
            shortest = reference_distance(graph, start, goal)
            if shortest is None:
                self.assertIsNone(path, (start, goal))
            else:
                self.assertValidPath(graph, path, start, goal)
                self.assertGreaterEqual(len(path) - 1, shortest)

    # ---------------- what the heuristic does ----------------
    def test_with_no_heuristic_it_explores_like_bfs(self):
        graph = GridGraph(Vault())
        no_idea = lambda tile, goal: 0
        greedy_order = [s.current for s in greedy.search(graph, (2, 13), (26, 14), no_idea)]
        bfs_order = [s.current for s in bfs.search(graph, (2, 13), (26, 14))]
        self.assertEqual(greedy_order, bfs_order)

    def test_records_the_cost_of_every_discovered_tile(self):
        graph = GridGraph(Vault())
        last = list(greedy.search(graph, (2, 13), (2, 2)))[-1]
        self.assertEqual(last.cost_so_far[(2, 13)], 0.0)
        self.assertEqual(set(last.cost_so_far), set(last.came_from))


if __name__ == "__main__":
    unittest.main()
