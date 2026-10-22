"""Binary heap stored in a list.

Min-heap (default): the smallest key sits at the root. Used for blood stock, keyed on expiry
date, so the unit closest to expiry is always issued first (FEFO).

Max-heap (max_heap=True): the largest key sits at the root. Used for emergency requests,
keyed on (priority, -arrival order) so the most urgent, earliest request is served first.

push and pop are O(log n). peek is O(1).
"""


class Heap:
    def __init__(self, key=lambda item: item, max_heap=False):
        self._a = []
        self._key = key
        self._max = max_heap

    def _before(self, i, j):
        ki, kj = self._key(self._a[i]), self._key(self._a[j])
        return ki > kj if self._max else ki < kj

    def _swap(self, i, j):
        self._a[i], self._a[j] = self._a[j], self._a[i]

    def push(self, item):
        self._a.append(item)
        i = len(self._a) - 1
        while i > 0:
            parent = (i - 1) // 2
            if not self._before(i, parent):
                break
            self._swap(i, parent)
            i = parent

    def pop(self):
        """Remove and return the root, or None when the heap is empty (underflow)."""
        if not self._a:
            return None
        root = self._a[0]
        last = self._a.pop()
        if self._a:
            self._a[0] = last
            i, n = 0, len(self._a)
            while True:
                left, right, best = 2 * i + 1, 2 * i + 2, i
                if left < n and self._before(left, best):
                    best = left
                if right < n and self._before(right, best):
                    best = right
                if best == i:
                    break
                self._swap(i, best)
                i = best
        return root

    def peek(self):
        return self._a[0] if self._a else None

    def remove_where(self, predicate):
        """Remove every item matching predicate by rebuilding the heap (used by Undo)."""
        keep = [item for item in self._a if not predicate(item)]
        self._a = []
        for item in keep:
            self.push(item)

    def to_list(self):
        """Items in heap (array) order."""
        return list(self._a)

    def in_order(self):
        """Items in priority order. A sorted copy, the heap itself is not changed."""
        return sorted(self._a, key=self._key, reverse=self._max)

    def __len__(self):
        return len(self._a)

    def __bool__(self):
        return bool(self._a)

    def __iter__(self):
        return iter(self.in_order())  # priority order, heap untouched

    def __repr__(self):
        return "Heap(%s, size=%d)" % ("max" if self._max else "min", len(self._a))