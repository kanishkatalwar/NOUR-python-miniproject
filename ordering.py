"""Sorting and searching written out by hand for the lab comparison.

Every sort returns a new list and takes an optional key function.
bubble_sort and insertion_sort are O(n^2). merge_sort and quick_sort are O(n log n).
binary_search_lower is O(log n) and needs a list that is already sorted.
"""


def bubble_sort(items, key=lambda x: x):
    a = list(items)
    for i in range(len(a) - 1):
        swapped = False
        for j in range(len(a) - 1 - i):
            if key(a[j]) > key(a[j + 1]):
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a


def insertion_sort(items, key=lambda x: x):
    a = list(items)
    for i in range(1, len(a)):
        current = a[i]
        k = key(current)
        j = i - 1
        while j >= 0 and key(a[j]) > k:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = current
    return a


def merge_sort(items, key=lambda x: x):
    if len(items) < 2:
        return list(items)
    mid = len(items) // 2
    left = merge_sort(items[:mid], key)
    right = merge_sort(items[mid:], key)
    merged, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def quick_sort(items, key=lambda x: x):
    a = list(items)

    def sort(lo, hi):
        while lo < hi:
            pivot = key(a[(lo + hi) // 2])
            i, j = lo, hi
            while i <= j:
                while key(a[i]) < pivot:
                    i += 1
                while key(a[j]) > pivot:
                    j -= 1
                if i <= j:
                    a[i], a[j] = a[j], a[i]
                    i += 1
                    j -= 1
            # recurse into the smaller part first to keep the stack shallow
            if j - lo < hi - i:
                sort(lo, j)
                lo = i
            else:
                sort(i, hi)
                hi = j

    sort(0, len(a) - 1)
    return a


def binary_search_lower(sorted_items, target, key=lambda x: x):
    """Index of the first item whose key is >= target, plus the number of steps taken."""
    lo, hi, steps = 0, len(sorted_items), 0
    while lo < hi:
        steps += 1
        mid = (lo + hi) // 2
        if key(sorted_items[mid]) < target:
            lo = mid + 1
        else:
            hi = mid
    return lo, steps