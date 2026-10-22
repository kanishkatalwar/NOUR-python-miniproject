"""NOUR core: one BloodBank object that ties every data structure together.

    Donor records ............ HashTable (chaining)
    Donation history ......... SinglyLinkedList (one node per visit)
    Blood stock per group .... dict of 8 min-Heaps keyed on expiry date
    Emergency requests ....... max-Heap keyed on (priority, earlier arrival first)
    Routine requests ......... CircularQueue (fixed size)
    Undo ..................... Stack
    Compatibility ............ directed graph + BFS (compatibility.py)
    Reports .................. merge sort, quick sort, binary search (ordering.py)
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from request_queue import CircularQueue
from compatibility import GROUPS, rank_fallbacks
from registry import HashTable
from priority_store import Heap
from history import SinglyLinkedList
from ordering import binary_search_lower, merge_sort, quick_sort
from undo import Stack

MIN_STOCK = 6            # below this a group is LOW
HIGH_STOCK = 14          # at or above this a group is HIGH
SHELF_LIFE_DAYS = 35     # days a fresh unit lasts
EXPIRY_ALERT_DAYS = 3    # alert window
MIN_GAP_DAYS = 90        # default gap between two donations by the same donor
EMERGENCY_PRIORITY = 4   # priority 4 and 5 go to the emergency heap
QUEUE_SIZE = 6           # slots in the routine circular queue


@dataclass
class Donor:
    id: str
    name: str
    group: str
    history: SinglyLinkedList = field(default_factory=SinglyLinkedList)

    def last_donation(self):
        return self.history.tail.value if self.history.tail else None


@dataclass(frozen=True)
class Unit:
    id: str
    group: str
    expiry: date


@dataclass
class Request:
    id: str
    seq: int
    patient: str
    group: str
    units: int
    reason: str
    priority: int


# ---------- sample data ----------
STOCK_SEED = {  # days left on each unit
    "A+": [2, 6, 9, 11, 13, 15, 18, 21, 24, 27, 30, 33, 35, 38],
    "A-": [4, 12, 20, 29, 36],
    "B+": [1, 5, 8, 10, 14, 17, 19, 23, 26, 31, 34, 37],
    "B-": [7, 16, 25, 33],
    "AB+": [9, 15, 22, 28, 32, 38],
    "AB-": [13, 27],
    "O+": [3, 4, 7, 9, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 39],
    "O-": [2, 15, 31],
}
DONOR_SEED = [  # id, name, group, days ago of each donation (oldest first)
    ("D1042", "Aarav Mehta", "O-", [300, 210, 118]),
    ("D1043", "Priya Nair", "A+", [280, 185, 95]),
    ("D1051", "Rohan Iyer", "B+", [220, 128, 31]),
    ("D1058", "Sneha Kulkarni", "AB+", [150, 52]),
    ("D1064", "Imran Shaikh", "O+", [260, 170, 79]),
    ("D1077", "Kavya Reddy", "A-", [130]),
    ("D1085", "Dev Malhotra", "B-", [240, 148]),
    ("D1090", "Tanvi Joshi", "O-", [88]),
    ("D1103", "Farhan Qureshi", "AB-", [201, 105]),
    ("D1118", "Ananya Das", "A+", [64]),
    ("D1126", "Vikram Rao", "B+", [330, 238, 140]),
    ("D1131", "Meera Pillai", "O+", [172, 81]),
]
REQUEST_SEED = [  # patient, group, units, reason, priority
    ("Mohan Lal", "B+", 1, "Chronic anaemia", 2),
    ("Rakesh Patil", "O-", 2, "Trauma", 5),
    ("Asha Desai", "O+", 2, "Elective surgery", 3),
    ("Jagdish Rane", "A+", 1, "Scheduled transfusion", 1),
    ("Sunita Kamat", "A+", 1, "Emergency surgery", 4),
    ("Lata Chavan", "AB+", 1, "Chronic anaemia", 2),
]


class BloodBank:
    def __init__(self, today=None, min_gap=MIN_GAP_DAYS):
        self.today = today or date.today()
        self.min_gap = min_gap
        self.donors = HashTable(11)
        self.stock = {g: Heap(key=lambda u: u.expiry) for g in GROUPS}
        self.emergency = Heap(key=lambda r: (r.priority, -r.seq), max_heap=True)
        self.routine = CircularQueue(QUEUE_SIZE)
        self.undo_stack = Stack()
        self.activity = []
        self._unit_no = 2000
        self._req_no = 300

    # ---------- small helpers ----------
    def _log(self, message):
        self.activity.insert(0, "%s %s" % (datetime.now().strftime("%H:%M"), message))
        del self.activity[30:]

    def _new_unit(self, group, days_left):
        self._unit_no += 1
        return Unit("U-%d" % self._unit_no, group, self.today + timedelta(days=days_left))

    def days_left(self, unit):
        return (unit.expiry - self.today).days

    def counts(self):
        return {g: len(self.stock[g]) for g in GROUPS}

    def status(self, group):
        n = len(self.stock[group])
        if n < MIN_STOCK:
            return "LOW"
        return "HIGH" if n >= HIGH_STOCK else "OK"

    def _remove_unit(self, unit):
        self.stock[unit.group].remove_where(lambda u: u.id == unit.id)

    # ---------- donors (hash table + linked list) ----------
    def register_donor(self, donor_id, name, group):
        """Return the Donor, or raise ValueError for a duplicate ID or an unknown group."""
        if group not in GROUPS:
            raise ValueError("Unknown blood group '%s'." % group)
        donor = Donor(donor_id, name, group)
        if not self.donors.insert(donor_id, donor):
            existing, bucket, _ = self.donors.search(donor_id)
            raise ValueError("Donor ID %s already exists in bucket %d (%s)."
                             % (donor_id, bucket, existing.name))
        self._log("Registered donor %s (%s, %s)" % (donor_id, name, group))
        return donor

    def find_donor(self, donor_id):
        """Return (Donor or None, bucket index, comparisons made)."""
        return self.donors.search(donor_id)

    def eligibility(self, donor):
        """Return (eligible, days since last donation or None, next eligible date or None)."""
        last = donor.last_donation()
        if last is None:
            return True, None, None
        since = (self.today - last).days
        return since >= self.min_gap, since, last + timedelta(days=self.min_gap)

    def record_donation(self, donor_id):
        donor, _, _ = self.find_donor(donor_id)
        if donor is None:
            raise ValueError("No donor with ID %s." % donor_id)
        ok, since, next_date = self.eligibility(donor)
        if not ok:
            self._log("Blocked donation by %s: gap rule of %d days" % (donor_id, self.min_gap))
            raise ValueError("%s donated %d days ago. Eligible again on %s."
                             % (donor.name, since, next_date.strftime("%d %b %Y")))
        donor.history.append(self.today)
        unit = self._new_unit(donor.group, SHELF_LIFE_DAYS)
        self.stock[donor.group].push(unit)
        self.undo_stack.push(("donate", donor, unit))
        self._log("Donation by %s recorded, unit %s added to %s heap" % (donor_id, unit.id, donor.group))
        return unit

    # ---------- stock (array of min-heaps) ----------
    def receive_unit(self, group, days_left):
        unit = self._new_unit(group, days_left)
        self.stock[group].push(unit)
        self.undo_stack.push(("receive", unit))
        self._log("Received %s unit %s with %d days to expiry" % (group, unit.id, days_left))
        return unit

    def issue_unit(self, group):
        """Issue the unit closest to expiry (FEFO). Returns None when the heap is empty."""
        unit = self.stock[group].pop()
        if unit is None:
            self._log("Issue from %s failed: heap empty (underflow)" % group)
            return None
        self.undo_stack.push(("issue_one", unit))
        self._log("Issued %s unit %s (%d days left, earliest first)" % (group, unit.id, self.days_left(unit)))
        return unit

    # ---------- requests (max-heap + circular queue) ----------
    def raise_request(self, patient, group, units, reason, priority):
        """Return (Request, 'emergency' or 'routine'). Raises OverflowError if the routine queue is full."""
        if group not in GROUPS:
            raise ValueError("Unknown blood group '%s'." % group)
        req = Request("R-%d" % (self._req_no + 1), self._req_no + 1, patient, group, units, reason, priority)
        if priority >= EMERGENCY_PRIORITY:
            self.emergency.push(req)
            where = "emergency"
        else:
            self.routine.enqueue(req)   # raises OverflowError when full
            where = "routine"
        self._req_no += 1
        self._log("%s added to %s (priority %d)" % (req.id, where, priority))
        return req, where

    def process_next(self):
        """Serve the top emergency request, else the front routine request.

        Uses the exact blood group first, then the best fallbacks found by BFS.
        Returns (request, source, issued_units, units_still_missing).
        Raises IndexError when nothing is waiting.
        """
        if len(self.emergency):
            req, source = self.emergency.pop(), "emergency"
        elif not self.routine.is_empty():
            req, source = self.routine.dequeue(), "routine"
        else:
            self._log("Process next: no pending requests (underflow)")
            raise IndexError("No pending requests (underflow).")
        issued, need = [], req.units
        for group in [req.group] + rank_fallbacks(req.group, self.counts()):
            while need and len(self.stock[group]):
                issued.append(self.stock[group].pop())
                need -= 1
            if not need:
                break
        self.undo_stack.push(("issue", req, source, issued))
        used = ", ".join(sorted({u.group for u in issued})) or "nothing"
        self._log("%s (%s, %s) needs %dx %s, got %d from %s%s"
                  % (req.id, source, req.patient, req.units, req.group, len(issued), used,
                     ", short by %d" % need if need else ""))
        return req, source, issued, need

    # ---------- undo (stack) ----------
    def undo(self):
        """Reverse the latest donation, receipt or issue. Raises IndexError if nothing to undo."""
        action = self.undo_stack.pop()
        kind = action[0]
        if kind == "donate":
            _, donor, unit = action
            donor.history.remove_last()
            self._remove_unit(unit)
            text = "donation by %s" % donor.id
        elif kind == "receive":
            self._remove_unit(action[1])
            text = "receipt of %s unit %s" % (action[1].group, action[1].id)
        elif kind == "issue_one":
            unit = action[1]
            self.stock[unit.group].push(unit)
            text = "issue of %s unit %s" % (unit.group, unit.id)
        else:  # "issue" from process_next
            _, req, source, issued = action
            if source == "routine" and self.routine.is_full():
                self.undo_stack.push(action)
                raise OverflowError("Routine queue is full, so %s cannot be put back yet." % req.id)
            for unit in issued:
                self.stock[unit.group].push(unit)
            if source == "emergency":
                self.emergency.push(req)
            else:
                self.routine.enqueue_front(req)
            text = "processing of %s" % req.id
        self._log("Undid " + text)
        return text

    # ---------- alerts and reports ----------
    def all_units(self):
        return [u for g in GROUPS for u in self.stock[g].to_list()]

    def expiring_soon(self, days=EXPIRY_ALERT_DAYS):
        soon = [u for u in self.all_units() if self.days_left(u) <= days]
        return merge_sort(soon, key=lambda u: u.expiry)

    def low_groups(self):
        return [g for g in GROUPS if self.status(g) == "LOW"]

    def donors_by_last_donation(self):
        """Merge sort, oldest last donation first (these donors are due soonest)."""
        with_history = [d for d in self.donors.values() if d.last_donation()]
        return merge_sort(with_history, key=lambda d: d.last_donation())

    def units_by_expiry(self):
        """Quick sort across all groups."""
        return quick_sort(self.all_units(), key=lambda u: u.expiry)

    def first_unit_with_days_left(self, days):
        """Binary search: first unit (by expiry) that still has at least `days` left.

        Returns (unit or None, steps taken, total units searched).
        """
        units = self.units_by_expiry()
        index, steps = binary_search_lower(units, days, key=self.days_left)
        return (units[index] if index < len(units) else None), steps, len(units)

    # ---------- sample data ----------
    def load_sample_data(self):
        for group, days in STOCK_SEED.items():
            for d in days:
                self.stock[group].push(self._new_unit(group, d))
        for donor_id, name, group, ago in DONOR_SEED:
            donor = Donor(donor_id, name, group)
            for a in ago:
                donor.history.append(self.today - timedelta(days=a))
            self.donors.insert(donor_id, donor)
        for patient, group, units, reason, priority in REQUEST_SEED:
            self.raise_request(patient, group, units, reason, priority)
        self.activity.clear()
        self.undo_stack = Stack()
        return self 