"""Timing comparisons for the report. Every function returns rows of (name, milliseconds).

Numbers change from machine to machine. The ratios between the rows are what matter.
"""
import random
from time import perf_counter

from sorted_index import BinarySearchTree
from registry import HashTable
from priority_store import Heap
from ordering import binary_search_lower, bubble_sort, insertion_sort, merge_sort, quick_sort


def _time(fn):
    start = perf_counter()
    fn()
    return (perf_counter() - start) * 1000


def lookup_benchmark(n=10000, queries=1000, seed=11):
    """Find donors by ID: linear search vs binary search vs BST vs hash table."""
    rng = random.Random(seed)
    ids = list(range(1000, 1000 + n))
    rng.shuffle(ids)
    wanted = [ids[rng.randrange(n)] for _ in range(queries)]

    def linear():
        for target in wanted:
            for value in ids:
                if value == target:
                    break

    ordered = sorted(ids)

    def binary():
        for target in wanted:
            i, _ = binary_search_lower(ordered, target)

    tree = BinarySearchTree()
    for value in ids:                      # random order, so the tree stays fairly balanced
        tree.insert(value)

    def bst():
        for target in wanted:
            tree.search(target)

    table = HashTable(1009)
    for value in ids:
        table.insert("D%d" % value, value)

    def hashed():
        for target in wanted:
            table.search("D%d" % target)

    return [("Linear search", _time(linear)), ("Binary search (sorted)", _time(binary)),
            ("BST (random order)", _time(bst)), ("Hash table", _time(hashed))]


def bst_worst_case(n=2000, queries=1000):
    """Same BST, but the IDs arrive already sorted, so the tree becomes a chain."""
    balanced, chain = BinarySearchTree(), BinarySearchTree()
    keys = list(range(n))
    shuffled = keys[:]
    random.Random(3).shuffle(shuffled)
    for k in shuffled:
        balanced.insert(k)
    for k in keys:
        chain.insert(k)
    targets = [random.Random(5).randrange(n) for _ in range(queries)]
    rows = [("BST, random insert order (height %d)" % balanced.height(),
             _time(lambda: [balanced.search(t) for t in targets])),
            ("BST, sorted insert order (height %d)" % chain.height(),
             _time(lambda: [chain.search(t) for t in targets]))]
    return rows


def sorting_benchmark(n=2000, seed=21):
    rng = random.Random(seed)
    data = [rng.randrange(100000) for _ in range(n)]
    return [("Bubble sort", _time(lambda: bubble_sort(data))),
            ("Insertion sort", _time(lambda: insertion_sort(data))),
            ("Merge sort", _time(lambda: merge_sort(data))),
            ("Quick sort", _time(lambda: quick_sort(data))),
            ("Python sorted() for reference", _time(lambda: sorted(data)))]


def earliest_expiry_benchmark(n=3000, seed=31):
    """Insert n units, then issue them all in expiry order: sorted array vs min-heap."""
    rng = random.Random(seed)
    days = [rng.randrange(40000) for _ in range(n)]

    def sorted_array():
        arr = []                            # kept sorted, largest first so the earliest is at the end
        for value in days:
            arr.append(value)
            i = len(arr) - 1
            while i > 0 and arr[i - 1] < arr[i]:   # shift: O(n) per insert
                arr[i - 1], arr[i] = arr[i], arr[i - 1]
                i -= 1
        while arr:
            arr.pop()                       # O(1)

    def heap():
        h = Heap()
        for value in days:
            h.push(value)                   # O(log n)
        while len(h):
            h.pop()                         # O(log n)

    return [("Sorted array (insert shifts items)", _time(sorted_array)), ("Min-heap", _time(heap))]


def run_all():
    return [
        ("Donor lookup, 10,000 donors, 1,000 searches", lookup_benchmark()),
        ("BST worst case", bst_worst_case()),
        ("Sorting 2,000 donor records", sorting_benchmark()),
        ("Earliest-expiry unit, 3,000 units", earliest_expiry_benchmark()),
    ]


def print_report(sections):
    for title, rows in sections:
        print("\n" + title)
        print("-" * len(title))
        fastest = min(ms for _, ms in rows)
        for name, ms in rows:
            bar = "#" * max(1, int(30 * ms / max(m for _, m in rows)))
            tag = "  <- fastest" if ms == fastest else ""
            print("  %-38s %9.2f ms  %s%s" % (name, ms, bar, tag))