"""NOUR website server.

Run this file in PyCharm (right-click server.py, Run 'server'), then open
http://127.0.0.1:8000 in your browser. It opens automatically.

The page in web/index.html is only the screen. Every action (register, donate, issue,
process, undo, sorting, searching, benchmark) runs on the BloodBank object from
blood_bank.py, so the website uses your own hash table, heaps, queue, stack, graph and sorts.

Only Python's standard library is used, so there is nothing to install.
"""
import json
import os
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import benchmark
import forecast
from blood_bank import (BloodBank, HIGH_STOCK, MIN_GAP_DAYS, MIN_STOCK,
                        QUEUE_SIZE)
from compatibility import CAN_DONATE_TO, GROUPS, bfs_tree, rank_fallbacks

HOST = "127.0.0.1"
PORT = int(os.environ.get("NOUR_PORT", "8000"))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

bank = BloodBank().load_sample_data()
lock = threading.Lock()
WEEKLY_HISTORY = forecast.sample_weekly_history()


# ---------- converting Python objects to JSON ----------
def req_json(r):
    return {"id": r.id, "seq": r.seq, "patient": r.patient, "group": r.group,
            "units": r.units, "reason": r.reason, "priority": r.priority}


def describe_undo(action):
    kind = action[0]
    if kind == "donate":
        return "donation by %s" % action[1].id
    if kind == "receive":
        return "receipt of %s unit" % action[1].group
    if kind == "issue_one":
        return "issue of %s unit" % action[1].group
    return "processing of %s" % action[1].id


def build_state():
    b = bank
    top = b.undo_stack.peek()
    ordered = forecast.forecast_all(WEEKLY_HISTORY)
    compat = {}
    for g in GROUPS:
        compat[g] = {
            "order": [{"g": grp, "depth": depth, "from": parent} for grp, depth, parent in bfs_tree(g)],
            "ranked": rank_fallbacks(g, b.counts()),
        }
    rear = b.routine.rear_index()
    return {
        "today": b.today.isoformat(),
        "config": {"min": MIN_STOCK, "high": HIGH_STOCK, "queue": QUEUE_SIZE, "gap": MIN_GAP_DAYS},
        "can": CAN_DONATE_TO,
        "stock": {g: [{"id": u.id, "days": b.days_left(u)} for u in b.stock[g].to_list()] for g in GROUPS},
        "donors": [[{"id": key, "name": d.name, "group": d.group} for key, d in chain]
                   for chain in b.donors.buckets],
        "donorCount": len(b.donors),
        "emergency": [req_json(r) for r in b.emergency.in_order()],
        "routine": {"cap": b.routine.capacity, "front": b.routine.front, "count": b.routine.count,
                    "rear": rear, "slots": [req_json(s) if s else None for s in b.routine.slots]},
        "undo": {"depth": len(b.undo_stack), "top": describe_undo(top) if top else None},
        "activity": list(b.activity),
        "forecast": ordered,
        "history": WEEKLY_HISTORY,
        "compat": compat,
    }


def norm_id(value):
    value = str(value or "").strip().upper()
    if value.isdigit():
        value = "D" + value
    return value if re.fullmatch(r"D\d+", value) else None


def ok(message):
    return {"ok": True, "message": message, "kind": "ok"}


def fail(message):
    return {"ok": False, "message": message, "kind": "warn"}


# ---------- actions (each one runs on the BloodBank) ----------
def act_register(d):
    donor_id, name, group = norm_id(d.get("id")), str(d.get("name", "")).strip(), d.get("group")
    if not donor_id or not name:
        return fail("Enter an ID like D1149 and a name.")
    try:
        bank.register_donor(donor_id, name, group)
    except ValueError as err:
        return fail(str(err) + " Registration rejected.")
    _, bucket, _ = bank.find_donor(donor_id)
    return ok("%s registered in bucket %d." % (name, bucket))


def act_donate(d):
    bank.min_gap = max(1, int(d.get("gap") or MIN_GAP_DAYS))
    try:
        unit = bank.record_donation(norm_id(d.get("id")) or "")
    except ValueError as err:
        return fail(str(err))
    return ok("Donation recorded. Unit %s added to %s stock." % (unit.id, unit.group))


def act_receive(d):
    group, days = d.get("group"), min(42, max(1, int(d.get("days") or 35)))
    if group not in GROUPS:
        return fail("Unknown blood group.")
    unit = bank.receive_unit(group, days)
    return ok("Unit %s inserted into the %s heap." % (unit.id, group))


def act_issue(d):
    group = d.get("group")
    if group not in GROUPS:
        return fail("Unknown blood group.")
    unit = bank.issue_unit(group)
    if unit is None:
        return fail("%s is out of stock. Open Compatibility for fallback groups." % group)
    return ok("Issued %s, the %s unit closest to expiry (%d days left)." % (unit.id, group, bank.days_left(unit)))


def act_request(d):
    try:
        req, where = bank.raise_request(str(d.get("patient", "")).strip() or "Unnamed patient",
                                        d.get("group"), min(4, max(1, int(d.get("units") or 1))),
                                        str(d.get("reason") or "Scheduled transfusion"),
                                        int(d.get("priority") or 1))
    except OverflowError:
        return fail("Routine queue is full. Process a request first. This is the overflow case.")
    except ValueError as err:
        return fail(str(err))
    if where == "emergency":
        return ok("%s joined the emergency heap at priority %d." % (req.id, req.priority))
    return ok("%s joined the routine queue." % req.id)


def act_process(d):
    try:
        req, source, issued, missing = bank.process_next()
    except IndexError:
        return fail("No pending requests. The queues are empty.")
    parts = {}
    for u in issued:
        parts[u.group] = parts.get(u.group, 0) + 1
    text = ", ".join("%d× %s" % (n, g) for g, n in parts.items()) or "nothing"
    if missing:
        return {"ok": True, "kind": "warn", "message": "%s partly filled with %s, short by %d unit%s."
                % (req.id, text, missing, "" if missing == 1 else "s")}
    return ok("%s filled with %s." % (req.id, text))


def act_undo(d):
    try:
        return ok("Undone: %s." % bank.undo())
    except IndexError:
        return fail("Nothing to undo. The undo stack is empty.")
    except OverflowError as err:
        return fail(str(err))


ACTIONS = {"register": act_register, "donate": act_donate, "receive": act_receive,
           "issue": act_issue, "request": act_request, "process": act_process, "undo": act_undo}


# ---------- read-only queries ----------
def query_donor(donor_id, gap):
    bank.min_gap = max(1, gap)
    key = norm_id(donor_id) or str(donor_id).upper()
    donor, bucket, comparisons = bank.find_donor(key)
    out = {"found": donor is not None, "id": key, "bucket": bucket, "comparisons": comparisons}
    if donor:
        eligible, since, next_date = bank.eligibility(donor)
        out.update({
            "donor": {"id": donor.id, "name": donor.name, "group": donor.group,
                      "history": [d.isoformat() for d in donor.history]},
            "eligible": eligible, "since": since,
            "next": next_date.isoformat() if next_date else None})
    return out


def query_reports(days):
    donors = bank.donors_by_last_donation()                      # merge sort
    units = bank.units_by_expiry()                                # quick sort
    unit, steps, total = bank.first_unit_with_days_left(days)     # binary search
    return {
        "donors": [{"id": d.id, "name": d.name, "group": d.group, "last": d.last_donation().isoformat(),
                    "daysAgo": (bank.today - d.last_donation()).days} for d in donors],
        "units": [{"id": u.id, "group": u.group, "days": bank.days_left(u)} for u in units[:8]],
        "unitTotal": len(units),
        "search": {"days": days, "steps": steps, "total": total,
                   "unit": {"id": unit.id, "group": unit.group, "days": bank.days_left(unit)} if unit else None},
    }


def query_benchmark():
    return [{"title": title, "rows": [{"name": n, "ms": ms} for n, ms in rows]}
            for title, rows in benchmark.run_all()]


# ---------- HTTP plumbing ----------
class Handler(BaseHTTPRequestHandler):
    server_version = "NOUR"

    def log_message(self, fmt, *args):          # keep the Run window quiet
        pass

    def _send(self, status, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path in ("/", "/index.html"):
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html")
            if url.path == "/favicon.ico":
                return self._send(204, b"", "image/x-icon")
            with lock:
                if url.path == "/api/state":
                    return self._send(200, build_state())
                if url.path == "/api/donor":
                    return self._send(200, query_donor(q.get("id", [""])[0], int(q.get("gap", ["90"])[0] or 90)))
                if url.path == "/api/reports":
                    return self._send(200, query_reports(int(q.get("days", ["20"])[0] or 0)))
                if url.path == "/api/benchmark":
                    return self._send(200, query_benchmark())
            self._send(404, {"ok": False, "message": "Not found"})
        except Exception as err:                  # show the problem in the page instead of a blank screen
            self._send(500, {"ok": False, "message": "Server error: %s" % err})

    def do_POST(self):
        url = urlparse(self.path)
        name = url.path.rsplit("/", 1)[-1]
        action = ACTIONS.get(name)
        if not url.path.startswith("/api/") or action is None:
            return self._send(404, {"ok": False, "message": "Unknown action"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            with lock:
                result = action(payload)
                result["state"] = build_state()
            self._send(200, result)
        except Exception as err:
            self._send(500, {"ok": False, "message": "Server error: %s" % err, "kind": "warn"})


def main():
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        print("Port %d is busy. Close the other NOUR window, or set NOUR_PORT to another number." % PORT)
        return
    url = "http://%s:%d" % (HOST, PORT)
    print("NOUR website is running at " + url)
    print("Press the red Stop button in PyCharm (or Ctrl+C) to stop it.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()