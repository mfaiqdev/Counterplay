"""
Tests for the map-to-graph conversion (algorithms/grid_graph.py) and the
shared search helpers (algorithms/search_core.py).

Run from the project folder with:
    python -m unittest discover -s tests -v

Most tests use a tiny hand-made map, small enough to check by eye:

        x: 0 1 2 3 4
    y=0    # # # # #
    y=1    # . . . #
    y=2    # . # . #
    y=3    # . D . #        D = locked door at (2, 3)
    y=4    # # # # #
"""

import os
import sys
import unittest

# Make "algorithms" and "environment" importable from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment.vault import Vault
from algorithms.grid_graph import GridGraph
from algorithms.search_core import (
    manhattan, reconstruct_path, endpoints_are_valid, run_search, SearchStep,
)
from algorithms.data_structures import Queue

TINY_LAYOUT = [
    "#####",
    "#...#",
    "#.#.#",
    "#.D.#",
    "#####",
]


def tiny_vault():
    return Vault(TINY_LAYOUT)


class TestGridGraph(unittest.TestCase):
    def test_only_walkable_tiles_become_nodes(self):
        graph = GridGraph(tiny_vault())
        self.assertEqual(len(graph), 7)
        self.assertIn((1, 1), graph)
        self.assertNotIn((0, 0), graph)               # outer wall
        self.assertNotIn((2, 2), graph)               # inner wall

    def test_locked_door_is_blocked_by_default(self):
        graph = GridGraph(tiny_vault())
        self.assertNotIn((2, 3), graph)
        self.assertNotIn((2, 3), graph.neighbours((1, 3)))

    def test_locked_door_can_be_allowed(self):
        graph = GridGraph(tiny_vault(), through_locked_doors=True)
        self.assertEqual(len(graph), 8)
        self.assertIn((2, 3), graph.neighbours((1, 3)))

    def test_neighbours_come_in_clockwise_order(self):
        graph = GridGraph(tiny_vault())
        # From (1, 1): up is a wall, right is (2, 1), down is (1, 2), left is a wall.
        self.assertEqual(graph.neighbours((1, 1)), [(2, 1), (1, 2)])
        self.assertEqual(graph.neighbours((2, 1)), [(3, 1), (1, 1)])

    def test_each_edge_is_counted_once(self):
        self.assertEqual(GridGraph(tiny_vault()).edge_count(), 6)
        self.assertEqual(GridGraph(tiny_vault(), through_locked_doors=True).edge_count(), 8)

    def test_unknown_tile_has_no_neighbours(self):
        graph = GridGraph(tiny_vault())
        self.assertEqual(graph.neighbours((0, 0)), [])
        self.assertEqual(graph.neighbours((99, 99)), [])

    def test_real_level_has_300_walkable_tiles(self):
        self.assertEqual(len(GridGraph(Vault())), 300)

    def test_edges_go_both_ways_on_the_real_level(self):
        graph = GridGraph(Vault())
        for tile in graph.nodes:
            for neighbour in graph.neighbours(tile):
                self.assertIn(tile, graph.neighbours(neighbour))

    def test_graph_is_a_snapshot_of_the_map(self):
        vault = Vault()
        door = vault.locked_door_positions()[0]
        before = GridGraph(vault)
        vault.unlock_door(*door)
        after = GridGraph(vault)
        self.assertNotIn(door, before)                # old graph is unchanged
        self.assertIn(door, after)                    # a new graph sees the open door

    def test_every_step_costs_one_by_default(self):
        graph = GridGraph(tiny_vault())
        self.assertEqual(graph.cost((1, 1), (2, 1)), 1.0)
        self.assertEqual(graph.path_cost([(1, 1), (2, 1), (3, 1)]), 2.0)
        self.assertEqual(graph.path_cost([(1, 1)]), 0.0)

    def test_extra_cost_is_added_when_entering_a_tile(self):
        risky = {(2, 1): 5.0}
        graph = GridGraph(tiny_vault(), extra_cost=lambda tile: risky.get(tile, 0.0))
        self.assertEqual(graph.cost((1, 1), (2, 1)), 6.0)     # 1 step + 5 risk
        self.assertEqual(graph.cost((2, 1), (3, 1)), 1.0)     # leaving it is normal


class TestSearchCore(unittest.TestCase):
    def test_manhattan_distance(self):
        self.assertEqual(manhattan((0, 0), (3, 4)), 7)
        self.assertEqual(manhattan((5, 5), (5, 5)), 0)
        self.assertEqual(manhattan((2, 9), (6, 1)), manhattan((6, 1), (2, 9)))

    def test_reconstruct_path_follows_the_links(self):
        came_from = {(0, 0): None, (1, 0): (0, 0), (1, 1): (1, 0), (5, 5): (0, 0)}
        self.assertEqual(reconstruct_path(came_from, (1, 1)), [(0, 0), (1, 0), (1, 1)])

    def test_reconstruct_path_when_start_is_goal(self):
        self.assertEqual(reconstruct_path({(3, 3): None}, (3, 3)), [(3, 3)])

    def test_reconstruct_path_returns_none_if_goal_never_reached(self):
        self.assertIsNone(reconstruct_path({(0, 0): None}, (9, 9)))

    def test_endpoints_must_be_walkable(self):
        graph = GridGraph(tiny_vault())
        self.assertTrue(endpoints_are_valid(graph, (1, 1), (3, 3)))
        self.assertFalse(endpoints_are_valid(graph, (0, 0), (3, 3)))   # start in a wall
        self.assertFalse(endpoints_are_valid(graph, (1, 1), (2, 3)))   # goal is locked

    def test_run_search_collects_the_numbers(self):
        graph = GridGraph(tiny_vault())

        def fake_search():
            # A pretend search that expands two tiles and then finishes.
            frontier = Queue([(2, 1), (1, 2)])
            came_from = {(1, 1): None, (2, 1): (1, 1), (1, 2): (1, 1)}
            yield SearchStep((1, 1), frontier, came_from, nodes_expanded=1)
            frontier.dequeue()
            yield SearchStep((2, 1), frontier, came_from, nodes_expanded=2,
                             finished=True, path=[(1, 1), (2, 1)])

        result = run_search("Fake", fake_search(), graph)
        self.assertEqual(result.algorithm, "Fake")
        self.assertTrue(result.found)
        self.assertEqual(result.path, [(1, 1), (2, 1)])
        self.assertEqual(result.steps, 1)
        self.assertEqual(result.path_cost, 1.0)
        self.assertEqual(result.nodes_expanded, 2)
        self.assertEqual(result.nodes_discovered, 3)
        self.assertEqual(result.max_frontier_size, 2)
        self.assertGreaterEqual(result.time_ms, 0.0)

    def test_run_search_reports_no_path(self):
        graph = GridGraph(tiny_vault())

        def hopeless_search():
            yield SearchStep(None, Queue(), {(1, 1): None}, 0, finished=True, path=None)

        result = run_search("Fake", hopeless_search(), graph)
        self.assertFalse(result.found)
        self.assertEqual(result.steps, 0)
        self.assertEqual(result.path_cost, float("inf"))


if __name__ == "__main__":
    unittest.main()
