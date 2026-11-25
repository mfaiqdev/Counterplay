"""
Tests for A* Search (algorithms/astar.py).

Run from the project folder with:
    python -m unittest discover -s tests -v

What we check
-------------
* OPTIMAL: on hundreds of random pairs, A*'s path is exactly as short as the
  true shortest path (checked against the deque oracle).
* EFFICIENT: it expands far fewer tiles than BFS (24 instead of 116 on the
  way to the key).
* WEIGHTED: when some tiles cost extra (like tiles a camera can see), A*
  finds the truly cheapest path (checked against a separate Dijkstra
  oracle), and takes a detour when the detour is cheaper.
* With a heuristic of 0, A* becomes Dijkstra's algorithm and still finds the
  shortest path, only with more work.
"""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.vault import Vault, ITEM_KEY, ITEM_GOLD
from algorithms import astar, bfs
from algorithms.grid_graph import GridGraph
from algorithms.search_core import run_search
from search_helpers import (
    PathChecks, tiny_vault, find_item, reference_distance, reference_cost,
    random_pairs,
)


class TestAStar(PathChecks, unittest.TestCase):
    # ---------------- tiny map and edge cases ----------------
    def test_finds_the_route_on_the_tiny_map(self):
        path = astar.find_path(tiny_vault(), (1, 1), (3, 3))
        self.assertEqual(path, [(1, 1), (2, 1), (3, 1), (3, 2), (3, 3)])

    def test_start_equal_to_goal_is_a_one_tile_path(self):
        self.assertEqual(astar.find_path(tiny_vault(), (1, 1), (1, 1)), [(1, 1)])

    def test_goal_inside_a_wall_has_no_path(self):
        self.assertIsNone(astar.find_path(tiny_vault(), (1, 1), (2, 2)))

    def test_locked_door_is_a_wall_unless_allowed(self):
        self.assertIsNone(astar.find_path(tiny_vault(), (1, 1), (2, 3)))
        path = astar.find_path(tiny_vault(), (1, 1), (2, 3), through_locked_doors=True)
        self.assertEqual(path, [(1, 1), (1, 2), (1, 3), (2, 3)])

    # ---------------- optimal ----------------
    def test_is_as_short_as_the_oracle_on_random_pairs(self):
        vault = Vault()
        graph = GridGraph(vault)
        for start, goal in random_pairs(graph, 300, seed=2026):
            path = astar.find_path(vault, start, goal)
            shortest = reference_distance(graph, start, goal)
            if shortest is None:
                self.assertIsNone(path, (start, goal))
            else:
                self.assertValidPath(graph, path, start, goal)
                self.assertEqual(len(path) - 1, shortest, (start, goal))

    def test_shortest_path_to_the_gold_through_the_vault_door(self):
        vault = Vault()
        gold = find_item(vault, ITEM_GOLD)
        path = astar.find_path(vault, vault.start, gold, through_locked_doors=True)
        self.assertEqual(len(path) - 1, 32)                    # Greedy takes 40

    # ---------------- efficient ----------------
    def test_expands_far_fewer_tiles_than_bfs(self):
        vault = Vault()
        graph = GridGraph(vault)
        key = find_item(vault, ITEM_KEY)
        a_star = run_search("A*", astar.search(graph, vault.start, key), graph)
        breadth = run_search("BFS", bfs.search(graph, vault.start, key), graph)
        self.assertEqual(a_star.steps, breadth.steps)          # same length: 15
        self.assertEqual(a_star.nodes_expanded, 24)
        self.assertEqual(breadth.nodes_expanded, 116)

    def test_never_expands_more_than_bfs_on_average(self):
        vault = Vault()
        graph = GridGraph(vault)
        a_star_total = bfs_total = 0
        for start, goal in random_pairs(graph, 200, seed=11):
            a_star_total += run_search("A*", astar.search(graph, start, goal), graph).nodes_expanded
            bfs_total += run_search("BFS", bfs.search(graph, start, goal), graph).nodes_expanded
        self.assertLess(a_star_total, bfs_total / 2)

    # ---------------- weighted (risky tiles) ----------------
    def test_takes_a_detour_when_a_tile_is_too_risky(self):
        risky = lambda tile: 5.0 if tile == (2, 1) else 0.0
        # Without risk, the route over the top through (2, 1) is shortest.
        # With risk, going down the left side and through the door is cheaper.
        path = astar.find_path(tiny_vault(), (1, 1), (3, 3),
                               through_locked_doors=True, extra_cost=risky)
        self.assertEqual(path, [(1, 1), (1, 2), (1, 3), (2, 3), (3, 3)])

    def test_finds_the_cheapest_path_with_random_risk(self):
        vault = Vault()
        rng = random.Random(3)
        risk = {tile: rng.choice([0.0, 0.0, 0.0, 2.0, 5.0]) for tile in GridGraph(vault).nodes}
        graph = GridGraph(vault, extra_cost=lambda tile: risk[tile])
        for start, goal in random_pairs(graph, 150, seed=5):
            result = run_search("A*", astar.search(graph, start, goal), graph)
            cheapest = reference_cost(graph, start, goal)
            if cheapest is None:
                self.assertFalse(result.found)
            else:
                self.assertValidPath(graph, result.path, start, goal)
                self.assertAlmostEqual(result.path_cost, cheapest, places=6)

    def test_with_no_heuristic_it_is_dijkstra(self):
        graph = GridGraph(Vault())
        no_idea = lambda tile, goal: 0
        for start, goal in random_pairs(graph, 50, seed=9):
            result = run_search("Dijkstra", astar.search(graph, start, goal, no_idea), graph)
            shortest = reference_distance(graph, start, goal)
            self.assertEqual(result.steps if result.found else None, shortest)

    # ---------------- the pausable search ----------------
    def test_reports_g_values(self):
        graph = GridGraph(Vault())
        last = list(astar.search(graph, (2, 13), (2, 2)))[-1]
        self.assertTrue(last.finished)
        self.assertEqual(last.cost_so_far[(2, 13)], 0.0)
        self.assertEqual(last.cost_so_far[(2, 2)], 15.0)


if __name__ == "__main__":
    unittest.main()
