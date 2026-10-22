"""Hash table with separate chaining (used for donor records).

Keys look like "D1042". The bucket is the numeric part of the key mod table size.
Average lookup, insert and delete are O(1). Duplicate keys are rejected.
"""


class HashTable:
    def __init__(self, size=11):
        self.size = size
        self.buckets = [[] for _ in range(size)]  # each bucket is a chain of (key, value)
        self.count = 0

    def _hash(self, key):
        digits = "".join(ch for ch in key if ch.isdigit())
        if digits:
            return int(digits) % self.size
        return sum(ord(ch) for ch in key) % self.size

    def insert(self, key, value):
        """Return True if inserted, False if the key already exists (duplicate check)."""
        chain = self.buckets[self._hash(key)]
        for existing_key, _ in chain:
            if existing_key == key:
                return False
        chain.append((key, value))
        self.count += 1
        return True

    def search(self, key):
        """Return (value or None, bucket_index, comparisons_made)."""
        index = self._hash(key)
        comparisons = 0
        for existing_key, value in self.buckets[index]:
            comparisons += 1
            if existing_key == key:
                return value, index, comparisons
        return None, index, comparisons

    def delete(self, key):
        chain = self.buckets[self._hash(key)]
        for i, (existing_key, _) in enumerate(chain):
            if existing_key == key:
                del chain[i]
                self.count -= 1
                return True
        return False

    def values(self):
        for chain in self.buckets:
            for _, value in chain:
                yield value

    def __len__(self):
        return self.count

    def __contains__(self, key):
        return self.search(key)[0] is not None

    def __getitem__(self, key):
        value = self.search(key)[0]
        if value is None:
            raise KeyError(key)
        return value

    def __iter__(self):
        return self.values()