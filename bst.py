"""Binary search tree (unbalanced), used only to compare donor lookup against the hash table.

Search and insert are O(log n) on random input and O(n) when keys arrive already sorted,
because the tree then degenerates into a linked list. The benchmark shows both cases.
"""


class BSTNode:
    def __init__(self, key, value=None):
        self.key = key
        self.value = value
        self.left = None
        self.right = None


class BinarySearchTree:
    def __init__(self):
        self.root = None
        self.size = 0

    def insert(self, key, value=None):
        """Return False when the key already exists."""
        node = BSTNode(key, value)
        if self.root is None:
            self.root = node
            self.size = 1
            return True
        current = self.root
        while True:
            if key == current.key:
                return False
            if key < current.key:
                if current.left is None:
                    current.left = node
                    break
                current = current.left
            else:
                if current.right is None:
                    current.right = node
                    break
                current = current.right
        self.size += 1
        return True

    def search(self, key):
        """Return (value or None, comparisons_made)."""
        current, comparisons = self.root, 0
        while current:
            comparisons += 1
            if key == current.key:
                return current.value, comparisons
            current = current.left if key < current.key else current.right
        return None, comparisons

    def height(self):
        """Longest root-to-leaf path, counted in nodes. Iterative to avoid recursion limits."""
        if self.root is None:
            return 0
        best, stack = 0, [(self.root, 1)]
        while stack:
            node, depth = stack.pop()
            best = max(best, depth)
            if node.left:
                stack.append((node.left, depth + 1))
            if node.right:
                stack.append((node.right, depth + 1))
        return best

    def in_order(self):
        """Keys in ascending order."""
        out, stack, current = [], [], self.root
        while stack or current:
            while current:
                stack.append(current)
                current = current.left
            current = stack.pop()
            out.append(current.key)
            current = current.right
        return out