"""Fixed-size circular queue (used for routine requests).

front and count track the occupied slots, and the rear index wraps around with modulo.
enqueue on a full queue raises OverflowError. dequeue on an empty queue raises IndexError.
Both operations are O(1).
"""


class CircularQueue:
    def __init__(self, capacity):
        self.capacity = capacity
        self.slots = [None] * capacity
        self.front = 0
        self.count = 0

    def is_full(self):
        return self.count == self.capacity

    def is_empty(self):
        return self.count == 0

    def rear_index(self):
        return (self.front + self.count - 1) % self.capacity if self.count else None

    def enqueue(self, item):
        if self.is_full():
            raise OverflowError("Routine queue is full (overflow).")
        self.slots[(self.front + self.count) % self.capacity] = item
        self.count += 1

    def dequeue(self):
        if self.is_empty():
            raise IndexError("No pending requests (underflow).")
        item = self.slots[self.front]
        self.slots[self.front] = None
        self.front = (self.front + 1) % self.capacity
        self.count -= 1
        return item

    def enqueue_front(self, item):
        """Put an item back at the front (used when Undo returns a request)."""
        if self.is_full():
            raise OverflowError("Routine queue is full (overflow).")
        self.front = (self.front - 1) % self.capacity
        self.slots[self.front] = item
        self.count += 1

    def items(self):
        return [self.slots[(self.front + i) % self.capacity] for i in range(self.count)]