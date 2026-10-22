"""Blood compatibility as a directed graph, searched with BFS.

Nodes are the 8 blood groups. An edge X -> Y means X can donate to Y.
To find every acceptable donor for a recipient, BFS runs over the reversed edges,
starting at the recipient. Time is O(V + E).
"""
from collections import deque

GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

CAN_DONATE_TO = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}


def reverse_graph():
    """recipient -> list of groups that can give to it (self loops left out)."""
    rev = {g: [] for g in GROUPS}
    for donor in GROUPS:
        for recipient in CAN_DONATE_TO[donor]:
            if donor != recipient:
                rev[recipient].append(donor)
    return rev


def bfs_donors(recipient):
    """Return [(group, depth), ...] in BFS order. The recipient itself is first at depth 0."""
    rev = reverse_graph()
    visited = {recipient}
    order = []
    queue = deque([(recipient, 0)])
    while queue:
        group, depth = queue.popleft()
        order.append((group, depth))
        for donor in rev[group]:
            if donor not in visited:
                visited.add(donor)
                queue.append((donor, depth + 1))
    return order


def bfs_tree(recipient):
    """Same search as bfs_donors, but also records which group each donor was found from.

    Returns [(group, depth, parent_or_None), ...] in BFS order. Used by the website.
    """
    rev = reverse_graph()
    visited = {recipient}
    order = []
    queue = deque([(recipient, 0, None)])
    while queue:
        group, depth, parent = queue.popleft()
        order.append((group, depth, parent))
        for donor in rev[group]:
            if donor not in visited:
                visited.add(donor)
                queue.append((donor, depth + 1, group))
    return order


def rank_fallbacks(recipient, stock_counts):
    """Other groups that could give to the recipient, best choice first.

    Groups that can donate to few others go first, so universal donors such as O-
    are kept for last. Ties are broken by how much stock is on hand.
    """
    others = [g for g, _ in bfs_donors(recipient)[1:]]
    return sorted(others, key=lambda g: (len(CAN_DONATE_TO[g]), -stock_counts.get(g, 0)))