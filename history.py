"""Singly linked list with a tail pointer (used for donation history per donor).

Appending a visit is O(1) because the tail pointer is kept. Removing the last node
(needed by Undo) walks from the head, so it is O(n).
"""


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None


class SinglyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.length = 0

    def append(self, value):
        node = Node(value)
        if self.head is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self.length += 1

    def remove_last(self):
        if self.head is None:
            return None
        removed = self.tail.value
        if self.head is self.tail:
            self.head = self.tail = None
        else:
            prev = self.head
            while prev.next is not self.tail:
                prev = prev.next
            prev.next = None
            self.tail = prev
        self.length -= 1
        return removed

    def __iter__(self):
        node = self.head
        while node:
            yield node.value
            node = node.next

    def __len__(self):
        return self.length