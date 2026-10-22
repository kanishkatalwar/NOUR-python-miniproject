"""Unit tests. In PyCharm: right-click this file, then Run 'Python tests in test_nour'."""
import random
import unittest
from datetime import date, timedelta

from blood_bank import BloodBank, QUEUE_SIZE
from sorted_index import BinarySearchTree
from request_queue import CircularQueue
from compatibility import CAN_DONATE_TO, GROUPS, bfs_donors, rank_fallbacks
from forecast import exponential_smoothing
from registry import HashTable
from priority_store import Heap
from history import SinglyLinkedList
from ordering import binary_search_lower, bubble_sort, insertion_sort, merge_sort, quick_sort
from undo import Stack


class StructureTests(unittest.TestCase):
    def test_hash_table_chaining_and_duplicates(self):
        t = HashTable(11)
        self.assertTrue(t.insert("D1", "a"))
        self.assertTrue(t.insert("D12", "b"))          # 12 mod 11 = 1, same bucket as D1
        self.assertFalse(t.insert("D1", "again"))
        value, bucket, comparisons = t.search("D12")
        self.assertEqual((value, bucket, comparisons), ("b", 1, 2))
        self.assertTrue(t.delete("D1"))
        self.assertIsNone(t.search("D1")[0])
        self.assertEqual(len(t), 1)

    def test_linked_list(self):
        ll = SinglyLinkedList()
        for x in (1, 2, 3):
            ll.append(x)
        self.assertEqual(list(ll), [1, 2, 3])
        self.assertEqual(ll.remove_last(), 3)
        self.assertEqual(list(ll), [1, 2])
        ll.remove_last()
        ll.remove_last()
        self.assertIsNone(ll.remove_last())
        ll.append(9)
        self.assertEqual((ll.head.value, ll.tail.value), (9, 9))

    def test_min_and_max_heap(self):
        rng = random.Random(1)
        data = [rng.randrange(1000) for _ in range(200)]
        lo, hi = Heap(), Heap(max_heap=True)
        for x in data:
            lo.push(x)
            hi.push(x)
        self.assertEqual([lo.pop() for _ in data], sorted(data))
        self.assertEqual([hi.pop() for _ in data], sorted(data, reverse=True))
        self.assertIsNone(lo.pop())

    def test_circular_queue_wraps_and_limits(self):
        q = CircularQueue(3)
        for x in "abc":
            q.enqueue(x)
        with self.assertRaises(OverflowError):
            q.enqueue("d")
        self.assertEqual(q.dequeue(), "a")
        q.enqueue("d")                                  # wraps around to slot 0
        self.assertEqual(q.items(), ["b", "c", "d"])
        for _ in range(3):
            q.dequeue()
        with self.assertRaises(IndexError):
            q.dequeue()

    def test_stack(self):
        s = Stack()
        s.push(1)
        s.push(2)
        self.assertEqual((s.pop(), s.pop()), (2, 1))
        with self.assertRaises(IndexError):
            s.pop()

    def test_bst(self):
        t = BinarySearchTree()
        for k in (5, 3, 8, 1, 4):
            t.insert(k, "v%d" % k)
        self.assertFalse(t.insert(5))
        self.assertEqual(t.in_order(), [1, 3, 4, 5, 8])
        self.assertEqual(t.search(4), ("v4", 3))         # path 5 -> 3 -> 4
        self.assertEqual(t.search(99)[0], None)
        chain = BinarySearchTree()
        for k in range(50):
            chain.insert(k)
        self.assertEqual(chain.height(), 50)

    def test_graph_bfs(self):
        order = [g for g, _ in bfs_donors("AB+")]
        self.assertEqual(order[0], "AB+")
        self.assertEqual(sorted(order), sorted(GROUPS))  # AB+ receives from everyone
        self.assertEqual([g for g, _ in bfs_donors("O-")], ["O-"])
        self.assertEqual(sorted(g for g, _ in bfs_donors("A+")), sorted(["A+", "A-", "O+", "O-"]))
        for donor in GROUPS:
            for recipient in CAN_DONATE_TO[donor]:
                self.assertIn(donor, [g for g, _ in bfs_donors(recipient)])
        ranked = rank_fallbacks("A+", {g: 5 for g in GROUPS})
        self.assertEqual(ranked[-1], "O-")               # universal donor is used last

    def test_sorting_and_binary_search(self):
        rng = random.Random(2)
        data = [rng.randrange(500) for _ in range(300)]
        for fn in (bubble_sort, insertion_sort, merge_sort, quick_sort):
            self.assertEqual(fn(data), sorted(data), fn.__name__)
            self.assertEqual(fn(data, key=lambda x: -x), sorted(data, reverse=True), fn.__name__)
        s = sorted(data)
        i, _ = binary_search_lower(s, 250)
        self.assertTrue(i == len(s) or s[i] >= 250)
        self.assertTrue(i == 0 or s[i - 1] < 250)

    def test_forecast(self):
        self.assertAlmostEqual(exponential_smoothing([10, 10, 10]), 10)
        self.assertGreater(exponential_smoothing([5, 5, 5, 20]), 5)


class BloodBankTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 15)
        self.bank = BloodBank(today=self.today).load_sample_data()

    def test_duplicate_donor_rejected(self):
        with self.assertRaises(ValueError):
            self.bank.register_donor("D1042", "Someone", "A+")
        self.bank.register_donor("D2000", "New Donor", "B-")
        self.assertIsNotNone(self.bank.find_donor("D2000")[0])

    def test_gap_rule_blocks_early_donation(self):
        with self.assertRaises(ValueError):
            self.bank.record_donation("D1090")           # donated 88 days ago, gap is 90
        with self.assertRaises(ValueError):
            self.bank.record_donation("D1064")           # donated 79 days ago
        with self.assertRaises(ValueError):
            self.bank.record_donation("D9999")           # unknown donor

    def test_donation_adds_node_and_unit_then_undo(self):
        bank = BloodBank(today=self.today).load_sample_data()
        donor = bank.find_donor("D1118")[0]              # last donated 64 days ago
        bank.min_gap = 30
        nodes, units = len(donor.history), len(bank.stock["A+"])
        bank.record_donation("D1118")
        self.assertEqual((len(donor.history), len(bank.stock["A+"])), (nodes + 1, units + 1))
        bank.undo()
        self.assertEqual((len(donor.history), len(bank.stock["A+"])), (nodes, units))

    def test_issue_is_earliest_expiry_first(self):
        self.assertEqual(self.bank.days_left(self.bank.issue_unit("O+")), 3)
        self.assertEqual(self.bank.days_left(self.bank.issue_unit("O+")), 4)
        self.bank.undo()                                 # puts the 4-day unit back
        self.assertEqual(self.bank.days_left(self.bank.stock["O+"].peek()), 4)

    def test_emergency_beats_routine_and_fallback_used(self):
        req, source, issued, missing = self.bank.process_next()
        self.assertEqual((req.patient, source), ("Rakesh Patil", "emergency"))   # priority 5 first
        self.assertEqual(len(issued) + missing, req.units)
        req2, source2, _, _ = self.bank.process_next()
        self.assertEqual((req2.patient, source2), ("Sunita Kamat", "emergency"))
        req3, source3, _, _ = self.bank.process_next()
        self.assertEqual((req3.patient, source3), ("Mohan Lal", "routine"))      # arrival order

    def test_out_of_stock_uses_graph_fallback(self):
        bank = BloodBank(today=self.today)
        bank.receive_unit("O-", 10)
        bank.raise_request("Test", "A+", 1, "Trauma", 5)
        _, _, issued, missing = bank.process_next()
        self.assertEqual([u.group for u in issued], ["O-"])
        self.assertEqual(missing, 0)

    def test_routine_overflow_and_underflow(self):
        bank = BloodBank(today=self.today)
        for i in range(QUEUE_SIZE):
            bank.raise_request("P%d" % i, "O+", 1, "Scheduled transfusion", 1)
        with self.assertRaises(OverflowError):
            bank.raise_request("Extra", "O+", 1, "Scheduled transfusion", 1)
        for _ in range(QUEUE_SIZE):
            bank.process_next()
        with self.assertRaises(IndexError):
            bank.process_next()

    def test_undo_process_restores_everything(self):
        stock_before = self.bank.counts()
        pending = len(self.bank.emergency)
        self.bank.process_next()
        self.bank.undo()
        self.assertEqual(self.bank.counts(), stock_before)
        self.assertEqual(len(self.bank.emergency), pending)
        with self.assertRaises(IndexError):
            for _ in range(5):
                self.bank.undo()

    def test_reports(self):
        donors = self.bank.donors_by_last_donation()
        dates = [d.last_donation() for d in donors]
        self.assertEqual(dates, sorted(dates))
        units = self.bank.units_by_expiry()
        self.assertEqual([u.expiry for u in units], sorted(u.expiry for u in units))
        unit, steps, total = self.bank.first_unit_with_days_left(20)
        self.assertGreaterEqual(self.bank.days_left(unit), 20)
        self.assertLessEqual(steps, 8)
        self.assertGreater(total, 50)
        self.assertTrue(all(self.bank.days_left(u) <= 3 for u in self.bank.expiring_soon()))
        self.assertEqual(sorted(self.bank.low_groups()), sorted(["A-", "B-", "AB-", "O-"]))


if __name__ == "__main__":
    unittest.main()