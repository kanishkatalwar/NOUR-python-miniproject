"""Tests for the website back end (server.py). They call the same functions the web page uses."""
import unittest
from datetime import date

import server
from blood_bank import BloodBank


class ServerTests(unittest.TestCase):
    def setUp(self):
        server.bank = BloodBank(today=date(2026, 10, 18)).load_sample_data()

    def test_state_contains_everything_the_page_draws(self):
        s = server.build_state()
        for key in ("stock", "donors", "emergency", "routine", "undo", "activity", "forecast", "compat", "can"):
            self.assertIn(key, s)
        self.assertEqual(len(s["donors"]), 11)                       # 11 hash buckets
        self.assertEqual(s["emergency"][0]["patient"], "Rakesh Patil")  # max-heap order
        self.assertEqual(s["routine"]["count"], 4)
        self.assertEqual(sum(len(v) for v in s["stock"].values()), 64)

    def test_duplicate_register_and_gap_rule(self):
        self.assertFalse(server.act_register({"id": "D1042", "name": "X", "group": "A+"})["ok"])
        self.assertTrue(server.act_register({"id": "1500", "name": "New Donor", "group": "B-"})["ok"])
        self.assertFalse(server.act_donate({"id": "D1118", "gap": 90})["ok"])   # donated 64 days ago
        self.assertTrue(server.act_donate({"id": "D1118", "gap": 30})["ok"])

    def test_process_and_undo_round_trip(self):
        before = {g: len(h) for g, h in server.bank.stock.items()}
        self.assertTrue(server.act_process({})["ok"])
        self.assertEqual(server.build_state()["undo"]["depth"], 1)
        self.assertTrue(server.act_undo({})["ok"])
        self.assertEqual({g: len(h) for g, h in server.bank.stock.items()}, before)
        self.assertFalse(server.act_undo({})["ok"])

    def test_queue_overflow_message(self):
        results = [server.act_request({"patient": "P", "group": "O+", "units": 1, "priority": 1,
                                       "reason": "Scheduled transfusion"})["ok"] for _ in range(4)]
        self.assertEqual(results, [True, True, False, False])         # 4 already waiting, 6 slots

    def test_queries(self):
        info = server.query_donor("D1042", 90)
        self.assertTrue(info["found"])
        self.assertEqual((info["bucket"], info["comparisons"]), (8, 1))
        self.assertFalse(server.query_donor("D9999", 90)["found"])
        rep = server.query_reports(20)
        days = [d["daysAgo"] for d in rep["donors"]]
        self.assertEqual(days, sorted(days, reverse=True))           # oldest donation first
        self.assertGreaterEqual(rep["search"]["unit"]["days"], 20)


if __name__ == "__main__":
    unittest.main()