# PawPal+

**PawPal+** is a Streamlit app that helps pet owners plan and track daily care tasks across multiple pets. It generates a prioritised, conflict-checked daily schedule that fits within the time you have available.

---

## Features

### Priority-based greedy scheduling
The scheduler (`Scheduler.generate()`) sorts all due tasks by a four-key rule before fitting them into the day's time budget:
1. **Time slot** — morning tasks are always considered before afternoon, then evening, then anytime.
2. **Priority** — high before medium before low within each slot.
3. **Medication first** — `meds` tasks are promoted ahead of other categories at equal priority.
4. **Shorter tasks first** — when two tasks tie on all other keys, the shorter one is scheduled first to maximise the number of tasks that fit.

Tasks that exceed the remaining budget are skipped and named in the explanation.

### Sorting by time
`Scheduler.sort_by_time()` orders any task list chronologically by `scheduled_time` (`HH:MM`). Each time string is parsed into an `(hour, minute)` integer tuple before comparison, so `09:05 < 09:30 < 14:00` is always correct regardless of string-sorting edge cases. Tasks with no scheduled time are pushed to the end of the list.

### Daily and weekly recurrence
Completing a task automatically queues its next occurrence:
- **Daily** — a fresh copy is appended with `due_date = today + 1 day`.
- **Weekly** — a fresh copy is appended with `due_date = today + 7 days`.
- **As-needed** — marked done with no follow-up created.

`Pet.undo_complete()` reverses this cleanly: the original task returns to pending and the auto-generated copy is removed.

### Conflict warnings
`Scheduler.detect_conflicts()` runs three independent checks after every schedule is built:
1. **Slot capacity** — warns if tasks in a named slot exceed its time limit (morning: 120 min; afternoon/evening: 90 min).
2. **Duplicate categories** — warns if the same pet has two tasks of the same category (e.g. two walks) in the same slot.
3. **Exact time collisions** — warns if two or more tasks share an identical `scheduled_time`, whether on the same pet or different pets.

Each check is isolated in its own `try/except` so a malformed time value produces a warning string instead of crashing the app.

### Filtering
Both `Owner.filter_tasks()` and `Scheduler.filter_tasks()` accept any `(Pet, Task)` list and narrow it by pet name, completion status (`pending` / `completed`), or both. The original list is never modified, so filters can be chained freely with `sort_by_time()`.

### Plain-language schedule explanation
Every generated schedule includes a human-readable summary (`schedule.explanation`) that names how many tasks were scheduled, which tasks were skipped due to time, and which recurring tasks are not yet due.

---

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

---

## Project files

| File | Purpose |
|---|---|
| `pawpal_system.py` | Core logic — `Task`, `Pet`, `Owner`, `Schedule`, `Scheduler` |
| `app.py` | Streamlit UI |
| `tests/test_pawpal.py` | Automated test suite (76 tests) |
| `uml_final.png` | Final class diagram |
| `uml_final.mmd` | Mermaid source for the class diagram |
| `reflection.md` | Design decisions and project reflection |

---

## Smarter Scheduling

The core scheduling logic lives in `pawpal_system.py` and has been extended beyond the original priority-based greedy fit with the following features.

### Time-slot ordering
Tasks carry a `time_slot` field (`morning`, `afternoon`, `evening`, `anytime`). The scheduler sorts by slot order before priority, so morning tasks are always considered first regardless of how they were entered.

### Exact-time sorting
Tasks optionally carry a `scheduled_time` in `HH:MM` format. `Scheduler.sort_by_time()` converts each string to an integer `(hour, minute)` tuple for comparison, ensuring `09:05 < 09:30 < 14:00` without string-lexicography edge cases. Tasks without a time are pushed to the end of the list.

### Filtering by pet or status
`Scheduler.filter_tasks()` accepts any `(Pet, Task)` list and narrows it by pet name, completion status (`pending` / `completed`), or both. It returns a new list and leaves the original unchanged, so it can be chained freely with `sort_by_time()`.

### Recurring tasks
`Task.is_due_today()` respects the task's `frequency` field:
- **daily** — always due unless already completed.
- **weekly** — due again after 7 days, tracked via `last_completed_date` and `timedelta`.
- **as-needed** — due until explicitly marked complete.

When `Pet.complete_task()` marks a daily or weekly task done, it automatically appends a fresh copy with the correct `due_date` (`today + 1` or `today + 7`). `Pet.undo_complete()` reverses this cleanly, removing the auto-generated copy.

### Conflict detection
`Scheduler.detect_conflicts()` runs three independent checks after the schedule is built:
1. **Slot capacity** — warns if total task time in a named slot exceeds its limit (morning: 120 min, afternoon/evening: 90 min).
2. **Duplicate categories** — warns if the same pet has two tasks of the same category (e.g. two walks) in the same slot.
3. **Exact time collisions** — warns if two or more tasks (same pet or different pets) share an identical `scheduled_time`.

Each check runs inside its own `try/except`, so a malformed time value produces a warning string rather than crashing the app. Tasks without a `scheduled_time` are skipped by check 3 and never produce false positives.

**Known tradeoff:** check 3 only detects identical start times, not overlapping durations. A 30-minute task at `09:00` and a task at `09:15` will not be flagged. Pet care routines are intentionally flexible, so exact-match catches the only unambiguous mistake (two tasks literally at the same moment) without producing noise for the expected case where tasks run back-to-back with natural gaps.

---

## Testing PawPal+

Tests live in `tests/test_pawpal.py` and cover the full scheduling pipeline.

### Running the tests

```bash
python3 -m pytest tests/test_pawpal.py -v
```

All 76 tests should pass.

### What is tested

| Category | Examples |
|---|---|
| **Sorting correctness** | Tasks returned in chronological `HH:MM` order; untimed tasks sorted last |
| **Recurrence logic** | Completing a daily task creates a follow-up due tomorrow; weekly follow-up due in 7 days; as-needed tasks produce no follow-up |
| **Conflict detection** | Duplicate times on the same or different pets; slot overbooked; same pet with two tasks of the same category in one slot |
| **Happy paths** | Full budget fits all tasks; overdue weekly task appears; normal schedule has no conflicts |
| **Edge cases** | Pet with no tasks; `available_minutes=0`; `undo_complete` on a never-completed task; weekly boundary at exactly 7 days; malformed `scheduled_time` produces a warning, not a crash |

### Known behaviour to be aware of

`complete_task` matches by title, so calling it twice on a task with a pending recurring copy (same title) will complete the copy and chain a second follow-up. Guard against double-completion in the UI layer.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
