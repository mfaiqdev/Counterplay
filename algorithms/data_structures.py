"""
data_structures.py - Our own Queue, Stack and MinHeap.

Why write our own instead of using Python's built-ins?
------------------------------------------------------
Python already has collections.deque (a queue) and heapq (a heap).  This is a
DSA project, so we build them ourselves to show how they work on the inside
and what every operation costs.  The tests in tests/test_data_structures.py
check that our versions give exactly the same answers as Python's.

Which search algorithm uses which structure
-------------------------------------------
    BFS     -> Queue    first in, first out: explores the map in rings
    DFS     -> Stack    last in, first out: dives deep, then backtracks
    Greedy  -> MinHeap  always takes the tile that LOOKS closest to the goal
    A*      -> MinHeap  always takes the tile with the smallest f = g + h

All three structures support len(), "if structure:" (True when not empty)
and iteration (for the visualizer), so the search code reads naturally.
"""


# ---------------------------------------------------------------------------
# Queue (built on a singly linked list)
# ---------------------------------------------------------------------------
class _Node:
    """One box in the linked list: a value and a pointer to the next box."""

    __slots__ = ("value", "next")      # saves memory: a node has only these two fields

    def __init__(self, value):
        self.value = value
        self.next = None


class Queue:
    """
    First In, First Out (FIFO), like the line at a bank counter.

    Built as a singly linked list with two pointers:

        head                         tail
         |                            |
        [A] --> [B] --> [C] --> [D] --> None
      (leaves first)            (joined last)

        enqueue  O(1)   attach a new node after the tail
        dequeue  O(1)   detach the head node
        peek     O(1)

    Why not a plain Python list?  list.pop(0) has to shift every remaining
    item one place to the left, which is O(n).  With head and tail pointers
    we never walk or shift anything.
    """

    def __init__(self, items=None):
        self._head = None
        self._tail = None
        self._size = 0
        if items is not None:
            for item in items:
                self.enqueue(item)

    def enqueue(self, item):
        """Add an item at the back of the line.  O(1)."""
        node = _Node(item)
        if self._tail is None:          # empty queue: the new node is both ends
            self._head = node
        else:
            self._tail.next = node      # link the old last node to the new one
        self._tail = node
        self._size += 1

    def dequeue(self):
        """Remove and return the item at the front.  O(1)."""
        if self._head is None:
            raise IndexError("dequeue from an empty Queue")
        node = self._head
        self._head = node.next
        if self._head is None:          # we just removed the only item
            self._tail = None
        self._size -= 1
        return node.value

    def peek(self):
        """Return the front item without removing it.  O(1)."""
        if self._head is None:
            raise IndexError("peek at an empty Queue")
        return self._head.value

    def is_empty(self):
        return self._size == 0

    def __len__(self):
        return self._size

    def __iter__(self):
        """Walk from front to back without removing anything.  O(n)."""
        node = self._head
        while node is not None:
            yield node.value
            node = node.next

    def __repr__(self):
        return "Queue(" + repr(list(self)) + ")"


# ---------------------------------------------------------------------------
# Stack (built on a dynamic array)
# ---------------------------------------------------------------------------
class Stack:
    """
    Last In, First Out (LIFO), like a stack of plates.

    Built on a Python list used as a dynamic array.  The TOP of the stack is
    the END of the list, so pushing and popping never shift other items:

        bottom                 top
        [A,  B,  C,  D]  <-- push / pop happen here

        push  O(1) amortised   list.append
        pop   O(1)             list.pop()
        peek  O(1)

    "Amortised" means: once in a while the list is full and Python copies it
    into a bigger block of memory (O(n)), but the size doubles each time, so
    averaged over many pushes each one still costs O(1).
    """

    def __init__(self, items=None):
        self._items = list(items) if items is not None else []

    def push(self, item):
        """Put an item on top.  O(1) amortised."""
        self._items.append(item)

    def pop(self):
        """Remove and return the top item.  O(1)."""
        if not self._items:
            raise IndexError("pop from an empty Stack")
        return self._items.pop()

    def peek(self):
        """Return the top item without removing it.  O(1)."""
        if not self._items:
            raise IndexError("peek at an empty Stack")
        return self._items[-1]

    def is_empty(self):
        return not self._items

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        """Walk from the top down to the bottom without removing anything."""
        return reversed(self._items)

    def __repr__(self):
        return "Stack(" + repr(self._items) + ")"


# ---------------------------------------------------------------------------
# MinHeap (a binary heap stored inside a list)
# ---------------------------------------------------------------------------
class MinHeap:
    """
    A binary min-heap: it always hands back the SMALLEST item first.

    The heap is a complete binary tree, stored level by level in a list:

                    1                 list index:        0
                 /     \\
                3       2                            1       2
               / \\     /
              7   4   5                            3   4   5

        list = [1, 3, 2, 7, 4, 5]

        parent of index i   = (i - 1) // 2
        children of index i = 2*i + 1  and  2*i + 2

    The one rule, the "heap property": every parent <= its children.
    That is why the smallest item is always at index 0.

        push     O(log n)   add at the end, then "sift up"
        pop      O(log n)   move the last item to the top, then "sift down"
        peek     O(1)
        build    O(n)       MinHeap(items) heapifies a whole list at once

    Items can be anything that works with <.  The search algorithms push
    tuples such as (f, h, counter, tile).  Python compares tuples from left
    to right, so the smallest f comes out first and the later fields break
    ties.
    """

    def __init__(self, items=None):
        self._data = list(items) if items is not None else []
        # Bottom-up heapify: fix every parent, starting from the last one.
        # Leaves (the second half of the list) are already valid heaps.
        for index in reversed(range(len(self._data) // 2)):
            self._sift_down(index)

    def push(self, item):
        """Add an item.  O(log n)."""
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def pop(self):
        """Remove and return the smallest item.  O(log n)."""
        if not self._data:
            raise IndexError("pop from an empty MinHeap")
        smallest = self._data[0]
        last = self._data.pop()          # take the last item out of the list
        if self._data:                   # if items remain, move it to the top
            self._data[0] = last
            self._sift_down(0)
        return smallest

    def peek(self):
        """Return the smallest item without removing it.  O(1)."""
        if not self._data:
            raise IndexError("peek at an empty MinHeap")
        return self._data[0]

    def is_empty(self):
        return not self._data

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        """Every item in list (heap) order, NOT sorted order.  O(n)."""
        return iter(self._data)

    def __repr__(self):
        return "MinHeap(" + repr(self._data) + ")"

    # ------------------------------------------------------------------
    # Keeping the heap property
    # ------------------------------------------------------------------
    def _sift_up(self, index):
        """Move the item at 'index' up while it is smaller than its parent."""
        while index > 0:
            parent = (index - 1) // 2
            if self._data[index] < self._data[parent]:
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sift_down(self, index):
        """Move the item at 'index' down while a child is smaller than it."""
        size = len(self._data)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < size and self._data[left] < self._data[smallest]:
                smallest = left
            if right < size and self._data[right] < self._data[smallest]:
                smallest = right
            if smallest == index:        # both children are bigger: done
                return
            self._swap(index, smallest)
            index = smallest

    def _swap(self, i, j):
        self._data[i], self._data[j] = self._data[j], self._data[i]
