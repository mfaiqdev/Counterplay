"""
Checks that run on ALL FOUR search algorithms at once.

Run from the project folder with:
    python -m unittest discover -s tests -v

Every algorithm must:
* offer the same interface (NAME, find_path, search), so the game can swap them
* agree with the others on WHETHER a path exists
* return only valid paths, never shorter than the true shortest path
* handle the edge cases the same way (start == goal, goal in a wall)
And the two optimal ones (BFS and A*) must always agree on the length.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.vault import Vault
from algorithms import ALGORITHMS, BY_KEY, astar, bfs
from algorithms.grid_graph import GridGraph
from search_helpers import PathChecks, tiny_vault, reference_distance, random_pairs


class TestAllAlgorithms(PathChecks, unittest.TestCase):
    def test_all_four_are_registered(self):
        self.assertEqual([a.NAME for a in ALGORITHMS], ["BFS", "DFS", "Greedy", "A*"])
        self.assertEqual(sorted(BY_KEY), ["astar", "bfs", "dfs", "greedy"])

    def test_same_interface(self):
        for algorithm in ALGORITHMS:
            with self.subTest(algorithm=algorithm.NAME):
                self.assertTrue(callable(algorithm.find_path))
                self.assertTrue(callable(algorithm.search))

    def test_edge_cases_are_handled_the_same_way(self):
        for algorithm in ALGORITHMS:
            with self.subTest(algorithm=algorithm.NAME):
                self.assertEqual(algorithm.find_path(tiny_vault(), (1, 1), (1, 1)), [(1, 1)])
                self.assertIsNone(algorithm.find_path(tiny_vault(), (1, 1), (2, 2)))
                self.assertIsNone(algorithm.find_path(tiny_vault(), (1, 1), (2, 3)))

    def test_every_search_ends_with_a_finished_step(self):
        graph = GridGraph(Vault())
        for algorithm in ALGORITHMS:
            with self.subTest(algorithm=algorithm.NAME):
                steps = list(algorithm.search(graph, (2, 13), (2, 2)))
                self.assertTrue(steps[-1].finished)
                self.assertEqual(steps[-1].path[-1], (2, 2))

    def test_all_agree_on_whether_a_path_exists(self):
        vault = Vault()
        graph = GridGraph(vault)
        for start, goal in random_pairs(graph, 200, seed=99):
            shortest = reference_distance(graph, start, goal)
            for algorithm in ALGORITHMS:
                path = algorithm.find_path(vault, start, goal)
                if shortest is None:
                    self.assertIsNone(path, (algorithm.NAME, start, goal))
                else:
                    self.assertValidPath(graph, path, start, goal)
                    self.assertGreaterEqual(len(path) - 1, shortest)

    def test_bfs_and_astar_always_agree_on_length(self):
        vault = Vault()
        graph = GridGraph(vault)
        for start, goal in random_pairs(graph, 200, seed=100):
            a = bfs.find_path(vault, start, goal)
            b = astar.find_path(vault, start, goal)
            self.assertEqual(a is None, b is None)
            if a is not None:
                self.assertEqual(len(a), len(b), (start, goal))


if __name__ == "__main__":
    unittest.main()
