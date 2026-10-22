# NOUR: Network for Organised Units & Records

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen) ![Tests](https://img.shields.io/badge/tests-23%20passing-brightgreen)

A blood bank management system built from data structures written by hand in Python: hash table, linked list, min/max heaps, circular queue, stack, graph with BFS, sorting and binary search. A built-in website shows every structure at work, and a small demand forecast adds an AI touch.

No packages to install. Pure Python standard library (`http.server`, `unittest`, `dataclasses`).

<!-- Add a screenshot: ![NOUR dashboard](docs/dashboard.png) -->

## What it does

- **Donors:** register, look up by ID, track donation history, enforce the minimum gap between donations (90 days by default).
- **Blood stock:** eight blood groups, each ordered by expiry so the unit closest to expiry is issued first. LOW / HIGH alerts and expiring-soon warnings.
- **Requests:** priority 4 and 5 go to an emergency queue, the rest to a routine queue. Process next fills the request and falls back to compatible groups when stock runs out.
- **Compatibility:** who can donate to whom, drawn as a graph, with fallback groups ranked so rare donors such as O- are used last.
- **Reports:** donors and units sorted, binary search by days to expiry, and live benchmarks of the algorithms.
- **Undo** for the last action, and a weekly **demand forecast** (exponential smoothing).

## Quick start

```bash
git clone https://github.com/kanishkatalwar/NOUR-python-miniproject.git
cd NOUR-python-miniproject
python server.py
```

The browser opens at http://127.0.0.1:8000. If port 8000 is busy, set `NOUR_PORT` to another number first.
Data lives in memory, so restarting the server resets the sample data.

Run the tests:

```bash
python -m unittest
```

## Data structures and where they are used

| File | Concept | Used for |
|---|---|---|
| `registry.py` | Hash table, separate chaining | Donor lookup by ID, duplicate check |
| `history.py` | Singly linked list with tail pointer | Donation history, one node per visit |
| `priority_store.py` | Min-heap and max-heap | Stock by expiry (min), emergency requests (max) |
| `request_queue.py` | Circular queue, fixed size | Routine requests, overflow and underflow |
| `undo.py` | Stack | Undo last action |
| `compatibility.py` | Directed graph, BFS | Who can donate to whom, fallback groups |
| `ordering.py` | Bubble, insertion, merge, quick sort, binary search | Reports and comparisons |
| `sorted_index.py` | Binary search tree | Compared against the hash table |
| `blood_bank.py` | Ties everything together | All business rules |
| `forecast.py` | Exponential smoothing | Demand forecast |
| `benchmark.py` | Timing comparisons | Report analysis |
| `server.py` + `web/index.html` | Website back end and page | The user interface |
| `test_nour.py`, `test_server.py` | Unit tests | 23 tests |

## Time complexity

| Operation | Structure | Complexity |
|---|---|---|
| Donor lookup | Hash table | O(1) average, O(n) worst case |
| Add a donation to history | Linked list (tail pointer) | O(1) |
| Issue the earliest-expiry unit | Min-heap | O(log n) |
| Next emergency request | Max-heap | O(log n) |
| Enqueue / dequeue routine request | Circular queue | O(1) |
| Undo | Stack | O(1) |
| Compatibility search | BFS on 8 nodes | O(V + E) |
| Sort donors or units | Merge sort / quick sort | O(n log n) |
| Find a unit by days left | Binary search | O(log n) |

## How the pieces connect

1. A donor registers and the hash table rejects duplicate IDs.
2. The last donation date is checked against the gap rule.
3. A donation adds a node to the donor's linked list and a unit to that group's min-heap.
4. A request goes to the emergency max-heap or the routine circular queue.
5. Process next tries the exact group, pops the earliest-expiry unit and pushes the action onto the undo stack.
6. If stock runs out, BFS over the compatibility graph finds fallback groups.

## Limitations and future scope

- Data is held in memory only. A database would keep it between runs.
- The forecast uses sample weekly history. Real issue records and a trained ML model would replace it.
- Future scope: SMS alerts to eligible donors, multi-hospital networks, expiry-aware transfers between banks.

## Team

-Sanskruti Sonawane
-Ridhima Swarup
-Kanishka Talwar
-Ishita Thakur