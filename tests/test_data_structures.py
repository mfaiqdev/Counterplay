"""
Tests for our own Queue, Stack and MinHeap (algorithms/data_structures.py).

Run from the project folder with:
    python -m unittest discover -s tests -v

Besides checking each structure on its own, these tests compare our versions
with Python's built-ins (collections.deque and heapq) on thousands of random
operations.  If ours ever gives a different answer, a test fails.
"""

import heapq
import os
import random
import sys
import unittest
from collections import deque

# Make "algorithms" importable no matter where the tests are started from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.data_structures import Queue, Stack, MinHeap


def heap_property_holds(heap):
    """True if every parent in the heap is <= its children."""
    data = list(heap)                     # heap order, as stored in the list
    for child in range(1, len(data)):
        parent = (child - 1) // 2
        if data[child] < data[parent]:
            return False
    return True


class TestQueue(unittest.TestCase):
    def test_first_in_first_out(self):
        queue = Queue()
        for letter in "ABCD":
            queue.enqueue(letter)
        self.assertEqual([queue.dequeue() for _ in range(4)], list("ABCD"))

    def test_empty_queue(self):
        queue = Queue()
        self.assertTrue(queue.is_empty())
        self.assertEqual(len(queue), 0)
        self.assertFalse(queue)                       # empty counts as False
        with self.assertRaises(IndexError):
            queue.dequeue()
        with self.assertRaises(IndexError):
            queue.peek()

    def test_peek_does_not_remove(self):
        queue = Queue([1, 2])
        self.assertEqual(queue.peek(), 1)
        self.assertEqual(len(queue), 2)

    def test_iteration_goes_front_to_back(self):
        queue = Queue([3, 1, 2])
        self.assertEqual(list(queue), [3, 1, 2])
        self.assertEqual(len(queue), 3)               # iterating removes nothing

    def test_can_be_reused_after_emptying(self):
        queue = Queue([1])
        queue.dequeue()
        queue.enqueue(2)                              # tail must have been reset
        queue.enqueue(3)
        self.assertEqual(list(queue), [2, 3])

    def test_matches_deque_on_random_operations(self):
        rng = random.Random(42)                       # fixed seed: same test every run
        ours, reference = Queue(), deque()
        for _ in range(5000):
            if reference and rng.random() < 0.45:
                self.assertEqual(ours.dequeue(), reference.popleft())
            else:
                value = rng.randint(0, 100)
                ours.enqueue(value)
                reference.append(value)
            self.assertEqual(len(ours), len(reference))
        self.assertEqual(list(ours), list(reference))


class TestStack(unittest.TestCase):
    def test_last_in_first_out(self):
        stack = Stack()
        for letter in "ABCD":
            stack.push(letter)
        self.assertEqual([stack.pop() for _ in range(4)], list("DCBA"))

    def test_empty_stack(self):
        stack = Stack()
        self.assertTrue(stack.is_empty())
        self.assertFalse(stack)
        with self.assertRaises(IndexError):
            stack.pop()
        with self.assertRaises(IndexError):
            stack.peek()

    def test_peek_shows_the_top(self):
        stack = Stack([1, 2, 3])
        self.assertEqual(stack.peek(), 3)
        self.assertEqual(len(stack), 3)

    def test_iteration_goes_top_to_bottom(self):
        stack = Stack([1, 2, 3])
        self.assertEqual(list(stack), [3, 2, 1])


class TestMinHeap(unittest.TestCase):
    def test_pops_in_sorted_order(self):
        heap = MinHeap()
        for number in [5, 3, 8, 1, 9, 2, 7]:
            heap.push(number)
        self.assertEqual([heap.pop() for _ in range(7)], [1, 2, 3, 5, 7, 8, 9])

    def test_empty_heap(self):
        heap = MinHeap()
        self.assertTrue(heap.is_empty())
        self.assertFalse(heap)
        with self.assertRaises(IndexError):
            heap.pop()
        with self.assertRaises(IndexError):
            heap.peek()

    def test_peek_shows_the_smallest(self):
        heap = MinHeap([4, 2, 6])
        self.assertEqual(heap.peek(), 2)
        self.assertEqual(len(heap), 3)

    def test_heap_property_after_every_push(self):
        heap = MinHeap()
        for number in [9, 4, 7, 1, 8, 2, 6, 3, 5, 0]:
            heap.push(number)
            self.assertTrue(heap_property_holds(heap))

    def test_building_from_a_list_heapifies_it(self):
        heap = MinHeap([9, 8, 7, 6, 5, 4, 3, 2, 1])
        self.assertTrue(heap_property_holds(heap))
        self.assertEqual(heap.pop(), 1)

    def test_duplicates_are_kept(self):
        heap = MinHeap([2, 1, 2, 1])
        self.assertEqual([heap.pop() for _ in range(4)], [1, 1, 2, 2])

    def test_tuples_compare_by_first_field_then_the_next(self):
        heap = MinHeap()
        heap.push((5, 0, "far"))
        heap.push((2, 1, "near, pushed second"))
        heap.push((2, 0, "near, pushed first"))
        self.assertEqual(heap.pop()[2], "near, pushed first")
        self.assertEqual(heap.pop()[2], "near, pushed second")
        self.assertEqual(heap.pop()[2], "far")

    def test_matches_heapq_on_random_operations(self):
        rng = random.Random(7)
        ours, reference = MinHeap(), []
        for _ in range(5000):
            if reference and rng.random() < 0.4:
                self.assertEqual(ours.pop(), heapq.heappop(reference))
            else:
                value = rng.randint(0, 1000)
                ours.push(value)
                heapq.heappush(reference, value)
            self.assertEqual(len(ours), len(reference))
        self.assertTrue(heap_property_holds(ours))


if __name__ == "__main__":
    unittest.main()
