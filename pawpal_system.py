from collections import Counter
from dataclasses import dataclass, field
from datetime import date as Date, timedelta

# Order in which time slots are scheduled (earlier = higher priority in sort)
SLOT_ORDER: dict[str, int] = {"morning": 0, "afternoon": 1, "evening": 2, "anytime": 3}

# Maximum minutes that can reasonably fit in each named slot
SLOT_CAPACITY: dict[str, int] = {"morning": 120, "afternoon": 90, "evening": 90}


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str            # "low", "medium", "high"
    category: str            # "walk", "feeding", "meds", "grooming", "enrichment"
    frequency: str = "daily"      # "daily", "weekly", "as-needed"
    time_slot: str = "anytime"    # "morning", "afternoon", "evening", "anytime"
    scheduled_time: str = ""      # specific start time in "HH:MM" format, e.g. "08:30"
    completed: bool = False
    last_completed_date: Date | None = None
    due_date: Date | None = None   # set on recurring copies: the date this copy becomes due
    recurring_copy: bool = False   # True when auto-created by next_occurrence()

    def mark_complete(self):
        """Mark this task as completed and record today's date for recurring logic."""
        self.completed = True
        self.last_completed_date = Date.today()

    def reset(self):
        """Undo completion so the task can be rescheduled."""
        self.completed = False
        self.last_completed_date = None

    def next_occurrence(self) -> "Task | None":
        """Return a fresh Task for the next recurrence, or None for as-needed tasks.

        due_date is calculated with timedelta so the new instance knows exactly
        when it becomes schedulable:
          - daily  → today + timedelta(days=1)   (tomorrow)
          - weekly → today + timedelta(days=7)   (same weekday, next week)

        The copy inherits all scheduling fields and is flagged recurring_copy=True
        so undo_complete() can locate and remove it.
        """
        if self.frequency == "as-needed":
            return None
        days_ahead = 1 if self.frequency == "daily" else 7
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            category=self.category,
            frequency=self.frequency,
            time_slot=self.time_slot,
            scheduled_time=self.scheduled_time,
            due_date=Date.today() + timedelta(days=days_ahead),
            recurring_copy=True,
        )

    def is_due_today(self) -> bool:
        """Return True if this task should appear in today's schedule.

        Recurring copies carry an explicit due_date (set by next_occurrence via
        timedelta).  For those, the check is simply due_date <= today.

        Original tasks without a due_date fall back to the legacy rules:
          - daily:     always due unless already completed.
          - weekly:    due if never completed, or last completion was 7+ days ago.
          - as-needed: due until explicitly marked complete.
        """
        if self.completed:
            return False
        if self.due_date is not None:
            return self.due_date <= Date.today()
        # --- legacy path for original (non-copy) tasks ---
        if self.frequency == "daily":
            return True
        if self.frequency == "weekly":
            if self.last_completed_date is None:
                return True
            return (Date.today() - self.last_completed_date).days >= 7
        # as-needed
        return True

    def is_urgent(self) -> bool:
        """Return True if this task has high priority."""
        return self.priority == "high"

    def __str__(self) -> str:
        status = "done" if self.completed else "pending"
        return (
            f"[{self.priority.upper()}] {self.title} "
            f"({self.duration_minutes} min, {self.frequency}, {self.time_slot}) — {status}"
        )


@dataclass
class Pet:
    name: str
    species: str
    age: int
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task):
        """Add a care task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str):
        """Remove a task from this pet's list by title."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def get_tasks(self) -> list[Task]:
        """Return all tasks assigned to this pet."""
        return self.tasks

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that have not yet been completed."""
        return [t for t in self.tasks if not t.completed]

    def get_due_tasks(self) -> list[Task]:
        """Return tasks that are due today, respecting each task's frequency rule.

        Delegates to ``Task.is_due_today()`` for each task, so the result
        automatically excludes:
          - Tasks already marked complete.
          - Weekly tasks completed within the last 7 days.
          - Recurring copies whose ``due_date`` has not yet arrived.

        Returns:
            A new list of Task objects that should appear in today's schedule.
            Returns an empty list if no tasks are currently due.
        """
        return [t for t in self.tasks if t.is_due_today()]

    def complete_task(self, title: str) -> "Task | None":
        """Mark a task complete and auto-append its next occurrence if recurring.

        For daily and weekly tasks, a fresh Task instance is appended to this
        pet's list so the next cycle appears automatically.  As-needed tasks
        are simply marked done with no follow-up created.

        Returns the newly created Task, or None if no follow-up was created.
        """
        task = next((t for t in self.tasks if t.title == title and not t.completed), None)
        if task is None:
            return None
        task.mark_complete()
        follow_up = task.next_occurrence()
        if follow_up is not None:
            self.tasks.append(follow_up)
        return follow_up

    def undo_complete(self, title: str) -> None:
        """Undo the most recent completion of a task and remove its auto-generated follow-up.

        Resets the completed task back to pending and removes the recurring_copy
        that complete_task() appended, keeping the list clean.
        """
        task = next((t for t in self.tasks if t.title == title and t.completed), None)
        if task is None:
            return
        task.reset()
        self.tasks = [
            t for t in self.tasks
            if not (t.title == title and t.recurring_copy and not t.completed)
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.species}, age {self.age})"


@dataclass
class Owner:
    name: str
    available_minutes: int
    preference: str = ""     # "morning", "evening", or ""
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet):
        """Add a pet to this owner's list of pets."""
        self.pets.append(pet)

    def remove_pet(self, name: str):
        """Remove a pet from this owner's list by name."""
        self.pets = [p for p in self.pets if p.name != name]

    def set_availability(self, minutes: int):
        """Update the number of minutes the owner has available today."""
        self.available_minutes = minutes

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return all tasks across all pets as (pet, task) pairs."""
        return [(pet, task) for pet in self.pets for task in pet.get_tasks()]

    def get_all_pending_tasks(self) -> list[tuple[Pet, Task]]:
        """Return only incomplete tasks across all pets as (pet, task) pairs."""
        return [(pet, task) for pet in self.pets for task in pet.get_pending_tasks()]

    def filter_tasks(
        self,
        pet_name: str | None = None,
        status: str | None = None,   # "pending", "completed", or None for all
    ) -> list[tuple[Pet, Task]]:
        """Return tasks filtered by pet name and/or completion status.

        Args:
            pet_name: If provided, only include tasks for this pet.
            status:   "pending" → incomplete only; "completed" → done only;
                      None → all tasks.
        """
        tasks = self.get_all_tasks()
        if pet_name:
            tasks = [(p, t) for p, t in tasks if p.name == pet_name]
        if status == "pending":
            tasks = [(p, t) for p, t in tasks if not t.completed]
        elif status == "completed":
            tasks = [(p, t) for p, t in tasks if t.completed]
        return tasks


class Schedule:
    def __init__(self, date: Date):
        self.date = date
        self.planned_tasks: list[tuple[Pet, Task]] = []
        self.conflicts: list[str] = []
        self.explanation: str = ""

    @property
    def total_duration(self) -> int:
        """Return the total duration of all planned tasks in minutes."""
        return sum(task.duration_minutes for _, task in self.planned_tasks)

    def add_task(self, pet: Pet, task: Task):
        """Add a (pet, task) pair to this schedule."""
        self.planned_tasks.append((pet, task))

    def remove_task(self, task: Task):
        """Remove a specific task from this schedule."""
        self.planned_tasks = [(p, t) for p, t in self.planned_tasks if t is not task]

    def get_summary(self) -> str:
        """Return a formatted plain-text summary of the day's schedule."""
        lines = [f"Schedule for {self.date}", f"Total time: {self.total_duration} min", ""]
        for pet, task in self.planned_tasks:
            lines.append(
                f"- [{task.priority.upper()}] {pet.name}: {task.title} "
                f"({task.duration_minutes} min, {task.time_slot})"
            )
        if self.conflicts:
            lines.append(f"\nConflicts: {'; '.join(self.conflicts)}")
        if self.explanation:
            lines.append(f"\nReasoning: {self.explanation}")
        return "\n".join(lines)


class Scheduler:
    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner):
        self.owner = owner

    def filter_tasks(
        self,
        tasks: list[tuple[Pet, Task]],
        pet_name: str | None = None,
        status: str | None = None,   # "pending", "completed", or None for all
    ) -> list[tuple[Pet, Task]]:
        """Filter a (pet, task) list by pet name and/or completion status.

        Args:
            tasks:    The task list to filter — pass owner.get_all_tasks(),
                      a schedule's planned_tasks, or any other (Pet, Task) list.
            pet_name: When given, keep only tasks belonging to this pet.
            status:   "pending"   → incomplete tasks only.
                      "completed" → completed tasks only.
                      None        → no status filter (return all).

        Returns a new list; the original is not modified.

        Example — pending tasks for one pet, sorted by time:
            filtered = scheduler.filter_tasks(
                owner.get_all_tasks(), pet_name="Mochi", status="pending"
            )
            ordered = scheduler.sort_by_time(filtered)
        """
        result = tasks
        if pet_name is not None:
            result = [(p, t) for p, t in result if p.name == pet_name]
        if status == "pending":
            result = [(p, t) for p, t in result if not t.completed]
        elif status == "completed":
            result = [(p, t) for p, t in result if t.completed]
        return result

    def _collect_tasks(self) -> list[tuple[Pet, Task]]:
        """Retrieve all tasks due today from every pet (respects frequency rules)."""
        return [(pet, task) for pet in self.owner.pets for task in pet.get_due_tasks()]

    def detect_conflicts(self, schedule: Schedule) -> list[str]:
        """Return a list of human-readable conflict descriptions.

        Each check runs independently inside its own try/except.  If a check
        encounters unexpected data (e.g. a malformed scheduled_time, a None
        field, or an unknown time_slot value) it appends a warning string and
        moves on — the other checks still run and the program never crashes.

        Checks:
        1. Slot capacity: total task time in a named slot exceeds its limit.
        2. Duplicate categories: same pet has more than one task of the same
           category in the same slot (e.g. two 'walk' tasks in morning).
        3. Exact time collisions: two or more tasks (same pet or different pets)
           share an identical scheduled_time in "HH:MM" format.

        Tradeoff — exact time match vs overlapping durations:
            Check 3 only flags tasks whose scheduled_time strings are identical
            (e.g. both "09:00").  It does NOT detect overlap, so a 30-minute
            task starting at "09:00" and a 20-minute task starting at "09:15"
            will silently coexist even though they run from 09:00–09:30 and
            09:15–09:35 respectively.

            Why this choice was made:
              - Tasks carry a scheduled_time but no scheduled_end_time.
                Computing overlap requires deriving an end time
                (start + duration_minutes) and comparing ranges — two extra
                steps that assume every scheduled_time is accurate and that
                tasks truly run back-to-back without gaps.
              - Exact-match catches the most obvious mistake (two tasks pinned
                to the same start time) with a simple dict-grouping approach
                that cannot itself crash or produce false positives.

            To upgrade to overlap detection in the future, derive each task's
            end time as a (hour, minute) integer pair and check whether any
            two intervals [start, start + duration) intersect.  This would
            catch the "09:00 + 30 min overlaps 09:15" case above, at the cost
            of more complex logic and a stricter requirement that
            scheduled_time values are always set and accurate.
        """
        conflicts = []

        # ── Check 1 & 2: slot capacity and duplicate categories ───────────────
        try:
            slot_groups: dict[str, list[tuple[Pet, Task]]] = {}
            for pet, task in schedule.planned_tasks:
                slot_groups.setdefault(task.time_slot, []).append((pet, task))

            for slot, items in slot_groups.items():
                cap = SLOT_CAPACITY.get(slot)
                if cap is not None:
                    total = sum(t.duration_minutes for _, t in items)
                    if total > cap:
                        conflicts.append(
                            f"{slot.capitalize()} slot overbooked: "
                            f"{total} min scheduled vs {cap} min capacity."
                        )

                per_pet: dict[str, list[str]] = {}
                for pet, task in items:
                    per_pet.setdefault(pet.name, []).append(task.category)
                for pet_name, cats in per_pet.items():
                    for cat, count in Counter(cats).items():
                        if count > 1:
                            conflicts.append(
                                f"{pet_name} has {count} '{cat}' tasks in the {slot} slot."
                            )
        except Exception as e:
            conflicts.append(f"Warning: slot/category check could not complete ({e}).")

        # ── Check 3: exact scheduled_time collisions ──────────────────────────
        try:
            time_groups: dict[str, list[tuple[Pet, Task]]] = {}
            for pet, task in schedule.planned_tasks:
                if not task.scheduled_time:
                    continue
                # Validate "HH:MM" format before using it as a group key
                parts = task.scheduled_time.split(":")
                if len(parts) != 2 or not all(p.isdigit() for p in parts):
                    conflicts.append(
                        f"Warning: '{task.title}' has an invalid scheduled_time "
                        f"'{task.scheduled_time}' — expected HH:MM."
                    )
                    continue
                time_groups.setdefault(task.scheduled_time, []).append((pet, task))

            for time_str, items in time_groups.items():
                if len(items) < 2:
                    continue
                labels = [f"{p.name}/'{t.title}'" for p, t in items]
                pet_names = {p.name for p, _ in items}
                if len(pet_names) == 1:
                    (owner_name,) = pet_names
                    conflicts.append(
                        f"Time collision at {time_str}: {owner_name} has "
                        f"{len(items)} tasks at the same time "
                        f"({', '.join(t.title for _, t in items)})."
                    )
                else:
                    conflicts.append(
                        f"Time collision at {time_str}: "
                        f"{' and '.join(labels)}."
                    )
        except Exception as e:
            conflicts.append(f"Warning: time-collision check could not complete ({e}).")

        return conflicts

    def sort_by_time(
        self, tasks: list[tuple[Pet, Task]]
    ) -> list[tuple[Pet, Task]]:
        """Sort (pet, task) pairs by scheduled_time in ascending chronological order.

        Converts each ``scheduled_time`` string from ``"HH:MM"`` into an
        ``(hour, minute)`` integer tuple before comparing, so numeric order is
        always correct — e.g. ``"09:05" < "09:30" < "14:00"`` — regardless of
        string lexicography edge cases such as single-digit hours.

        Tasks with no ``scheduled_time`` (empty string) are treated as
        ``(24, 0)`` and sorted to the end of the list.

        Args:
            tasks: A list of ``(Pet, Task)`` pairs to sort.  The original list
                   is not modified; a new sorted list is returned.

        Returns:
            A new list of ``(Pet, Task)`` pairs ordered earliest to latest by
            ``scheduled_time``, with un-timed tasks appended at the end.
        """
        return sorted(
            tasks,
            key=lambda pt: (
                tuple(int(x) for x in pt[1].scheduled_time.split(":"))
                if pt[1].scheduled_time
                else (24, 0)   # no time set → push to the end of the day
            ),
        )

    def generate(self) -> Schedule:
        """Build and return a Schedule by fitting due tasks within the owner's time budget.

        Algorithm (greedy, O(n log n)):
          1. Collect all tasks that are due today via ``_collect_tasks()``.
          2. Sort them by a four-key tuple:
               time slot order → priority (high first) →
               meds before other categories at equal priority →
               shorter duration first (maximises tasks that fit).
          3. Iterate through the sorted list; add each task to the schedule
             if its duration fits within the remaining budget.  A running
             ``used`` counter avoids re-summing the schedule on every step.
          4. Run ``detect_conflicts()`` on the finalised schedule.
          5. Generate a plain-text explanation via ``_explain()``.

        Returns:
            A ``Schedule`` instance for today containing:
              - ``planned_tasks``: the (Pet, Task) pairs that fit.
              - ``conflicts``:     any slot, category, or time warnings.
              - ``explanation``:   a human-readable summary of decisions made.
        """
        due = self._collect_tasks()

        sorted_tasks = sorted(
            due,
            key=lambda pt: (
                SLOT_ORDER.get(pt[1].time_slot, 3),
                self.PRIORITY_ORDER.get(pt[1].priority, 2),
                0 if pt[1].category == "meds" else 1,
                pt[1].duration_minutes,
            ),
        )

        schedule = Schedule(date=Date.today())
        used = 0  # running total — avoids re-summing the schedule on every iteration
        for pet, task in sorted_tasks:
            if used + task.duration_minutes <= self.owner.available_minutes:
                schedule.add_task(pet, task)
                used += task.duration_minutes

        schedule.conflicts = self.detect_conflicts(schedule)
        schedule.explanation = self._explain(schedule, due)
        return schedule

    def _explain(self, schedule: Schedule, all_due: list[tuple[Pet, Task]]) -> str:
        """Generate a plain-text explanation of scheduling decisions.

        Compares the finalised ``schedule`` against every task that was due
        today (``all_due``) to identify what was included, what was skipped
        due to the time budget, and what is not yet due (weekly tasks still
        within their 7-day window).

        Args:
            schedule:  The completed ``Schedule`` returned by ``generate()``.
            all_due:   Every ``(Pet, Task)`` pair that passed ``is_due_today()``
                       before the budget filter was applied.

        Returns:
            A single string summarising how many tasks were scheduled, which
            tasks were skipped (named individually), and which recurring tasks
            are not yet due.  Returns a short "no tasks" message when the
            schedule is empty.
        """
        if not schedule.planned_tasks:
            return "No tasks could fit within the available time."

        scheduled_ids = {id(t) for _, t in schedule.planned_tasks}
        skipped = [(p, t) for p, t in all_due if id(t) not in scheduled_ids]

        lines = [
            f"Scheduled {len(schedule.planned_tasks)} task(s) for {self.owner.name}'s pet(s), "
            f"fitting within {self.owner.available_minutes} available minutes."
        ]
        if skipped:
            names = ", ".join(f"'{t.title}' ({p.name})" for p, t in skipped)
            lines.append(f"Skipped due to time: {names}.")

        # Surface tasks that exist but aren't due yet (weekly not yet due)
        not_due = [
            (p, t) for p, t in self.owner.get_all_tasks()
            if not t.completed and not t.is_due_today()
        ]
        if not_due:
            nd_names = ", ".join(f"'{t.title}'" for _, t in not_due)
            lines.append(f"Not due yet (weekly): {nd_names}.")

        return " ".join(lines)
