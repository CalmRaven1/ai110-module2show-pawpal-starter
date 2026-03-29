import pytest
from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler, Schedule


# --- Fixtures ---

@pytest.fixture
def sample_pet():
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task(title="Morning walk",  duration_minutes=20, priority="high",   category="walk",       time_slot="morning"))
    pet.add_task(Task(title="Breakfast",     duration_minutes=5,  priority="high",   category="feeding",    time_slot="morning"))
    pet.add_task(Task(title="Puzzle toy",    duration_minutes=15, priority="low",    category="enrichment", time_slot="afternoon"))
    return pet


@pytest.fixture
def sample_owner(sample_pet):
    owner = Owner(name="Jordan", available_minutes=90, preference="morning")
    owner.add_pet(sample_pet)
    return owner


# --- Task: basic state ---

def test_task_is_urgent_high():
    task = Task(title="Meds", duration_minutes=5, priority="high", category="meds")
    assert task.is_urgent() is True

def test_task_is_not_urgent_low():
    task = Task(title="Grooming", duration_minutes=10, priority="low", category="grooming")
    assert task.is_urgent() is False

def test_task_mark_complete():
    task = Task(title="Walk", duration_minutes=20, priority="medium", category="walk")
    task.mark_complete()
    assert task.completed is True
    assert task.last_completed_date == date.today()

def test_task_reset_clears_date():
    task = Task(title="Walk", duration_minutes=20, priority="medium", category="walk")
    task.mark_complete()
    task.reset()
    assert task.completed is False


# --- Task: next_occurrence ---

def test_next_occurrence_daily_returns_fresh_task():
    task = Task(title="Walk", duration_minutes=20, priority="high",
                category="walk", frequency="daily", scheduled_time="07:30")
    task.mark_complete()
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.title == "Walk"
    assert nxt.completed is False
    assert nxt.last_completed_date is None
    assert nxt.scheduled_time == "07:30"
    assert nxt.recurring_copy is True

def test_next_occurrence_daily_due_date_is_tomorrow():
    task = Task(title="Walk", duration_minutes=20, priority="high",
                category="walk", frequency="daily")
    nxt = task.next_occurrence()
    assert nxt.due_date == date.today() + timedelta(days=1)

def test_next_occurrence_weekly_due_date_is_7_days():
    task = Task(title="Bath", duration_minutes=30, priority="medium",
                category="grooming", frequency="weekly")
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.frequency == "weekly"
    assert nxt.recurring_copy is True
    assert nxt.due_date == date.today() + timedelta(days=7)

def test_next_occurrence_as_needed_returns_none():
    task = Task(title="Vet visit", duration_minutes=60, priority="high",
                category="meds", frequency="as-needed")
    assert task.next_occurrence() is None

def test_is_due_today_respects_future_due_date():
    task = Task(title="Walk", duration_minutes=20, priority="high",
                category="walk", frequency="daily",
                due_date=date.today() + timedelta(days=1))
    assert task.is_due_today() is False

def test_is_due_today_respects_past_due_date():
    task = Task(title="Walk", duration_minutes=20, priority="high",
                category="walk", frequency="daily",
                due_date=date.today() - timedelta(days=1))
    assert task.is_due_today() is True

def test_is_due_today_true_when_due_date_is_today():
    task = Task(title="Walk", duration_minutes=20, priority="high",
                category="walk", frequency="daily",
                due_date=date.today())
    assert task.is_due_today() is True


# --- Pet: complete_task / undo_complete ---

def test_complete_task_daily_appends_follow_up(sample_pet):
    count_before = len(sample_pet.get_tasks())
    sample_pet.complete_task("Morning walk")
    assert len(sample_pet.get_tasks()) == count_before + 1

def test_complete_task_marks_original_done(sample_pet):
    sample_pet.complete_task("Morning walk")
    original = next(t for t in sample_pet.get_tasks() if t.title == "Morning walk" and t.completed)
    assert original.completed is True

def test_complete_task_follow_up_is_pending(sample_pet):
    sample_pet.complete_task("Morning walk")
    copies = [t for t in sample_pet.get_tasks()
              if t.title == "Morning walk" and t.recurring_copy]
    assert len(copies) == 1
    assert copies[0].completed is False

def test_complete_task_as_needed_no_follow_up(sample_pet):
    sample_pet.add_task(Task(title="Vet visit", duration_minutes=60,
                             priority="high", category="meds", frequency="as-needed"))
    count_before = len(sample_pet.get_tasks())
    sample_pet.complete_task("Vet visit")
    assert len(sample_pet.get_tasks()) == count_before   # no new task added

def test_complete_task_returns_none_for_as_needed(sample_pet):
    sample_pet.add_task(Task(title="Vet visit", duration_minutes=60,
                             priority="high", category="meds", frequency="as-needed"))
    result = sample_pet.complete_task("Vet visit")
    assert result is None

def test_undo_complete_resets_original(sample_pet):
    sample_pet.complete_task("Morning walk")
    sample_pet.undo_complete("Morning walk")
    original = next(t for t in sample_pet.get_tasks()
                    if t.title == "Morning walk" and not t.recurring_copy)
    assert original.completed is False

def test_undo_complete_removes_recurring_copy(sample_pet):
    sample_pet.complete_task("Morning walk")
    sample_pet.undo_complete("Morning walk")
    copies = [t for t in sample_pet.get_tasks() if t.recurring_copy]
    assert copies == []

def test_undo_complete_restores_original_count(sample_pet):
    count_before = len(sample_pet.get_tasks())
    sample_pet.complete_task("Morning walk")
    sample_pet.undo_complete("Morning walk")
    assert len(sample_pet.get_tasks()) == count_before


# --- Task: is_due_today ---

def test_daily_task_is_always_due():
    task = Task(title="Feed", duration_minutes=5, priority="high", category="feeding", frequency="daily")
    assert task.is_due_today() is True

def test_completed_task_is_not_due():
    task = Task(title="Feed", duration_minutes=5, priority="high", category="feeding")
    task.mark_complete()
    assert task.is_due_today() is False

def test_weekly_task_due_when_never_completed():
    task = Task(title="Bath", duration_minutes=20, priority="medium", category="grooming", frequency="weekly")
    assert task.is_due_today() is True

def test_weekly_task_not_due_within_7_days_even_if_not_completed():
    # last_completed_date 3 days ago means the weekly window hasn't elapsed —
    # the task is not due regardless of the completed flag.
    task = Task(title="Bath", duration_minutes=20, priority="medium", category="grooming", frequency="weekly")
    task.last_completed_date = date.today() - timedelta(days=3)
    assert task.is_due_today() is False

def test_weekly_task_due_after_7_days():
    task = Task(title="Bath", duration_minutes=20, priority="medium", category="grooming", frequency="weekly")
    task.last_completed_date = date.today() - timedelta(days=8)
    assert task.is_due_today() is True

def test_weekly_task_not_due_within_7_days():
    task = Task(title="Bath", duration_minutes=20, priority="medium", category="grooming", frequency="weekly")
    task.completed = True
    task.last_completed_date = date.today() - timedelta(days=2)
    assert task.is_due_today() is False

def test_as_needed_task_due_until_completed():
    task = Task(title="Vet visit", duration_minutes=60, priority="medium", category="meds", frequency="as-needed")
    assert task.is_due_today() is True
    task.mark_complete()
    assert task.is_due_today() is False


# --- Pet ---

def test_pet_add_task(sample_pet):
    initial_count = len(sample_pet.get_tasks())
    sample_pet.add_task(Task(title="Evening walk", duration_minutes=15, priority="medium", category="walk"))
    assert len(sample_pet.get_tasks()) == initial_count + 1

def test_pet_get_pending_tasks(sample_pet):
    sample_pet.get_tasks()[0].mark_complete()
    pending = sample_pet.get_pending_tasks()
    assert all(not t.completed for t in pending)

def test_pet_remove_task(sample_pet):
    sample_pet.remove_task("Breakfast")
    titles = [t.title for t in sample_pet.get_tasks()]
    assert "Breakfast" not in titles

def test_pet_get_due_tasks_excludes_completed(sample_pet):
    sample_pet.get_tasks()[0].mark_complete()
    due = sample_pet.get_due_tasks()
    assert all(t.title != "Morning walk" for t in due)

def test_pet_get_due_tasks_excludes_weekly_done_recently(sample_pet):
    weekly = Task(title="Bath", duration_minutes=20, priority="low",
                  category="grooming", frequency="weekly")
    weekly.completed = True
    weekly.last_completed_date = date.today() - timedelta(days=1)
    sample_pet.add_task(weekly)
    due_titles = [t.title for t in sample_pet.get_due_tasks()]
    assert "Bath" not in due_titles


# --- Owner ---

def test_owner_add_pet(sample_owner):
    new_pet = Pet(name="Luna", species="cat", age=2)
    sample_owner.add_pet(new_pet)
    assert any(p.name == "Luna" for p in sample_owner.pets)

def test_owner_get_all_pending_tasks(sample_owner):
    sample_owner.pets[0].get_tasks()[0].mark_complete()
    pairs = sample_owner.get_all_pending_tasks()
    assert all(not task.completed for _, task in pairs)

def test_owner_set_availability(sample_owner):
    sample_owner.set_availability(45)
    assert sample_owner.available_minutes == 45

def test_filter_tasks_by_pet(sample_owner):
    luna = Pet(name="Luna", species="cat", age=2)
    luna.add_task(Task(title="Dinner", duration_minutes=5, priority="high", category="feeding"))
    sample_owner.add_pet(luna)
    result = sample_owner.filter_tasks(pet_name="Luna")
    assert all(p.name == "Luna" for p, _ in result)
    assert len(result) == 1

def test_filter_tasks_pending_only(sample_owner):
    sample_owner.pets[0].get_tasks()[0].mark_complete()
    result = sample_owner.filter_tasks(status="pending")
    assert all(not t.completed for _, t in result)

def test_filter_tasks_completed_only(sample_owner):
    sample_owner.pets[0].get_tasks()[0].mark_complete()
    result = sample_owner.filter_tasks(status="completed")
    assert all(t.completed for _, t in result)
    assert len(result) == 1

def test_filter_tasks_all_returns_everything(sample_owner):
    sample_owner.pets[0].get_tasks()[0].mark_complete()
    result = sample_owner.filter_tasks()
    assert len(result) == len(sample_owner.pets[0].get_tasks())

def test_filter_tasks_by_pet_and_status(sample_owner):
    sample_owner.pets[0].get_tasks()[0].mark_complete()
    result = sample_owner.filter_tasks(
        pet_name="Mochi", status="completed"
    )
    assert len(result) == 1
    assert result[0][1].title == "Morning walk"


# --- Scheduler ---

def test_schedule_fits_within_budget(sample_owner):
    schedule = Scheduler(sample_owner).generate()
    assert schedule.total_duration <= sample_owner.available_minutes

def test_schedule_high_priority_tasks_included(sample_owner):
    schedule = Scheduler(sample_owner).generate()
    scheduled_titles = [t.title for _, t in schedule.planned_tasks]
    high_tasks = [t for t in sample_owner.pets[0].get_tasks() if t.is_urgent()]
    for task in high_tasks:
        assert task.title in scheduled_titles

def test_schedule_excludes_completed_tasks(sample_owner):
    sample_owner.pets[0].get_tasks()[0].mark_complete()
    schedule = Scheduler(sample_owner).generate()
    assert all(not t.completed for _, t in schedule.planned_tasks)

def test_schedule_respects_tight_budget(sample_owner):
    sample_owner.set_availability(10)
    schedule = Scheduler(sample_owner).generate()
    assert schedule.total_duration <= 10

def test_schedule_empty_when_no_tasks():
    owner = Owner(name="Alex", available_minutes=60)
    owner.add_pet(Pet(name="Empty", species="cat", age=1))
    schedule = Scheduler(owner).generate()
    assert schedule.planned_tasks == []

def test_schedule_sorted_by_slot_then_priority(sample_owner):
    schedule = Scheduler(sample_owner).generate()
    slots = [t.time_slot for _, t in schedule.planned_tasks]
    from pawpal_system import SLOT_ORDER
    slot_indices = [SLOT_ORDER.get(s, 3) for s in slots]
    assert slot_indices == sorted(slot_indices)

def test_schedule_meds_before_same_priority_category(sample_owner):
    pet = sample_owner.pets[0]
    pet.add_task(Task(title="Eye drops", duration_minutes=3, priority="high",
                      category="meds", time_slot="morning"))
    schedule = Scheduler(sample_owner).generate()
    morning_tasks = [t for _, t in schedule.planned_tasks if t.time_slot == "morning"]
    titles = [t.title for t in morning_tasks]
    if "Eye drops" in titles and "Morning walk" in titles:
        assert titles.index("Eye drops") < titles.index("Morning walk")

def test_schedule_excludes_weekly_task_completed_recently():
    owner = Owner(name="Sam", available_minutes=60)
    pet = Pet(name="Rex", species="dog", age=4)
    weekly = Task(title="Bath", duration_minutes=20, priority="medium",
                  category="grooming", frequency="weekly")
    weekly.completed = True
    weekly.last_completed_date = date.today() - timedelta(days=2)
    pet.add_task(weekly)
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert all(t.title != "Bath" for _, t in schedule.planned_tasks)

def test_schedule_includes_weekly_task_overdue():
    owner = Owner(name="Sam", available_minutes=60)
    pet = Pet(name="Rex", species="dog", age=4)
    weekly = Task(title="Nail trim", duration_minutes=10, priority="low",
                  category="grooming", frequency="weekly")
    weekly.last_completed_date = date.today() - timedelta(days=8)
    pet.add_task(weekly)
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert any(t.title == "Nail trim" for _, t in schedule.planned_tasks)


# --- Conflict detection ---

def test_no_conflicts_when_slots_within_capacity():
    owner = Owner(name="Casey", available_minutes=60)
    pet = Pet(name="Buddy", species="dog", age=2)
    pet.add_task(Task(title="Walk", duration_minutes=20, priority="high",
                      category="walk", time_slot="morning"))
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert schedule.conflicts == []

def test_conflict_slot_overbooked():
    owner = Owner(name="Casey", available_minutes=480)
    pet = Pet(name="Buddy", species="dog", age=2)
    # 5 × 30 min = 150 min in morning slot (capacity 120)
    for i in range(1, 6):
        pet.add_task(Task(title=f"Task {i}", duration_minutes=30, priority="high",
                          category="enrichment", time_slot="morning"))
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert any("overbooked" in c for c in schedule.conflicts)

def test_conflict_duplicate_category_same_slot():
    owner = Owner(name="Casey", available_minutes=120)
    pet = Pet(name="Buddy", species="dog", age=2)
    pet.add_task(Task(title="Walk A", duration_minutes=15, priority="high",
                      category="walk", time_slot="morning"))
    pet.add_task(Task(title="Walk B", duration_minutes=15, priority="high",
                      category="walk", time_slot="morning"))
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert any("walk" in c for c in schedule.conflicts)

def test_anytime_slot_has_no_capacity_conflict():
    owner = Owner(name="Casey", available_minutes=480)
    pet = Pet(name="Buddy", species="dog", age=2)
    for i in range(1, 6):
        pet.add_task(Task(title=f"Task {i}", duration_minutes=30, priority="high",
                          category="enrichment", time_slot="anytime"))
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    # "anytime" has no capacity limit — only duplicate-category conflicts possible
    assert not any("overbooked" in c for c in schedule.conflicts)


# --- Conflict detection: exact time collisions ---

def _make_owner_with_timed_tasks(*pet_task_pairs, budget=240):
    """Helper: build an Owner with one or more (pet_name, [(title, time)...]) specs."""
    owner = Owner(name="Test", available_minutes=budget)
    for pet_name, tasks in pet_task_pairs:
        pet = Pet(name=pet_name, species="dog", age=2)
        for title, stime in tasks:
            pet.add_task(Task(title=title, duration_minutes=5, priority="high",
                              category="walk", scheduled_time=stime))
        owner.add_pet(pet)
    return owner

def test_no_time_collision_when_times_differ():
    owner = _make_owner_with_timed_tasks(
        ("Rex",  [("Walk", "07:30"), ("Meds", "09:00")]),
    )
    schedule = Scheduler(owner).generate()
    assert not any("collision" in c for c in schedule.conflicts)

def test_same_pet_time_collision_detected():
    owner = _make_owner_with_timed_tasks(
        ("Rex", [("Walk", "08:00"), ("Breakfast", "08:00")]),
    )
    schedule = Scheduler(owner).generate()
    collision = [c for c in schedule.conflicts if "collision" in c.lower()]
    assert len(collision) == 1
    assert "08:00" in collision[0]
    assert "Rex" in collision[0]

def test_same_pet_collision_message_names_both_tasks():
    owner = _make_owner_with_timed_tasks(
        ("Rex", [("Walk", "08:00"), ("Breakfast", "08:00")]),
    )
    schedule = Scheduler(owner).generate()
    collision = next(c for c in schedule.conflicts if "collision" in c.lower())
    assert "Walk" in collision
    assert "Breakfast" in collision

def test_cross_pet_time_collision_detected():
    owner = _make_owner_with_timed_tasks(
        ("Rex",  [("Walk",     "08:00")]),
        ("Cleo", [("Flea meds","08:00")]),
    )
    schedule = Scheduler(owner).generate()
    collision = [c for c in schedule.conflicts if "collision" in c.lower()]
    assert len(collision) == 1
    assert "08:00" in collision[0]

def test_cross_pet_collision_message_names_both_pets():
    owner = _make_owner_with_timed_tasks(
        ("Rex",  [("Walk",      "08:00")]),
        ("Cleo", [("Flea meds", "08:00")]),
    )
    schedule = Scheduler(owner).generate()
    collision = next(c for c in schedule.conflicts if "collision" in c.lower())
    assert "Rex" in collision
    assert "Cleo" in collision

def test_tasks_without_scheduled_time_never_collide():
    # Tasks with scheduled_time="" should never trigger a time collision
    owner = Owner(name="Test", available_minutes=120)
    pet = Pet(name="Buddy", species="dog", age=2)
    pet.add_task(Task(title="Walk A", duration_minutes=15, priority="high", category="walk"))
    pet.add_task(Task(title="Walk B", duration_minutes=15, priority="high", category="walk"))
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert not any("collision" in c for c in schedule.conflicts)

def test_three_way_time_collision_reports_one_conflict():
    owner = _make_owner_with_timed_tasks(
        ("Rex",  [("Task A", "09:00")]),
        ("Cleo", [("Task B", "09:00")]),
        ("Pip",  [("Task C", "09:00")]),
    )
    schedule = Scheduler(owner).generate()
    collisions = [c for c in schedule.conflicts if "collision" in c.lower()]
    assert len(collisions) == 1   # one message per conflicting time slot
    assert "09:00" in collisions[0]


# --- Conflict detection: lightweight / graceful error handling ---

def _schedule_with_bad_task(scheduled_time):
    """Build a Schedule that contains a task with an arbitrary scheduled_time value."""
    schedule = Schedule(date=date.today())
    pet = Pet(name="Rex", species="dog", age=2)
    task = Task(title="Walk", duration_minutes=20, priority="high",
                category="walk", scheduled_time=scheduled_time)
    schedule.add_task(pet, task)
    return schedule

def test_malformed_time_returns_warning_not_exception():
    # "8:0" has single digits; "abc" is not numeric — both should warn, not crash
    for bad_time in ("8:0", "abc", "25:99", "08-00", ""):
        owner = Owner(name="Test", available_minutes=60)
        scheduler = Scheduler(owner)
        schedule = _schedule_with_bad_task(bad_time)
        # Must not raise — always returns a list
        result = scheduler.detect_conflicts(schedule)
        assert isinstance(result, list)

def test_malformed_time_message_contains_warning():
    schedule = _schedule_with_bad_task("not-a-time")
    owner = Owner(name="Test", available_minutes=60)
    conflicts = Scheduler(owner).detect_conflicts(schedule)
    warnings = [c for c in conflicts if c.lower().startswith("warning")]
    assert len(warnings) == 1
    assert "not-a-time" in warnings[0]

def test_valid_tasks_unaffected_alongside_bad_time(sample_owner):
    # Inject one bad task into an otherwise good schedule
    schedule = Scheduler(sample_owner).generate()
    bad_pet = Pet(name="Ghost", species="cat", age=1)
    bad_task = Task(title="Ghost walk", duration_minutes=10, priority="low",
                    category="walk", scheduled_time="bad_value")
    schedule.add_task(bad_pet, bad_task)
    # Slot/category checks (check 1 & 2) should still run and return no slot issues
    conflicts = Scheduler(sample_owner).detect_conflicts(schedule)
    slot_issues = [c for c in conflicts if "overbooked" in c or "tasks in the" in c]
    assert slot_issues == []   # no slot problems in this data
    # The bad time produces exactly one warning
    warnings = [c for c in conflicts if c.lower().startswith("warning")]
    assert len(warnings) == 1

def test_detect_conflicts_always_returns_list(sample_owner):
    # Guarantee the return type is always list[str] regardless of input state
    schedule = Scheduler(sample_owner).generate()
    result = Scheduler(sample_owner).detect_conflicts(schedule)
    assert isinstance(result, list)
    assert all(isinstance(c, str) for c in result)


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_happy_path_complete_and_schedule_next_day(sample_pet):
    """Completing a daily task marks it done and the follow-up is due tomorrow."""
    follow_up = sample_pet.complete_task("Morning walk")
    assert follow_up is not None
    assert follow_up.due_date == date.today() + timedelta(days=1)
    assert follow_up.completed is False

def test_happy_path_schedule_returns_all_tasks_when_budget_is_large():
    """When available_minutes far exceeds total task time, every due task is included."""
    owner = Owner(name="Jordan", available_minutes=9999)
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task(title="Walk",      duration_minutes=20, priority="high",   category="walk",    time_slot="morning"))
    pet.add_task(Task(title="Breakfast", duration_minutes=5,  priority="high",   category="feeding", time_slot="morning"))
    pet.add_task(Task(title="Puzzle",    duration_minutes=15, priority="low",    category="enrichment", time_slot="afternoon"))
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert len(schedule.planned_tasks) == 3

def test_happy_path_weekly_task_appears_when_overdue():
    """A weekly task last done 8 days ago is included in today's schedule."""
    owner = Owner(name="Sam", available_minutes=60)
    pet = Pet(name="Rex", species="dog", age=4)
    task = Task(title="Nail trim", duration_minutes=10, priority="low", category="grooming", frequency="weekly")
    task.last_completed_date = date.today() - timedelta(days=8)
    pet.add_task(task)
    owner.add_pet(pet)
    schedule = Scheduler(owner).generate()
    assert any(t.title == "Nail trim" for _, t in schedule.planned_tasks)

def test_happy_path_no_conflicts_in_normal_schedule(sample_owner):
    """A well-formed schedule with tasks spread across slots produces no conflicts."""
    schedule = Scheduler(sample_owner).generate()
    assert schedule.conflicts == []

def test_happy_path_sort_by_time_orders_correctly():
    """sort_by_time returns tasks in ascending HH:MM order."""
    owner = Owner(name="Test", available_minutes=120)
    scheduler = Scheduler(owner)
    pet = Pet(name="Buddy", species="dog", age=2)
    tasks = [
        (pet, Task(title="Evening",   duration_minutes=10, priority="low",  category="walk", scheduled_time="18:00")),
        (pet, Task(title="Morning",   duration_minutes=10, priority="high", category="walk", scheduled_time="07:00")),
        (pet, Task(title="Afternoon", duration_minutes=10, priority="low",  category="walk", scheduled_time="13:30")),
    ]
    result = scheduler.sort_by_time(tasks)
    titles = [t.title for _, t in result]
    assert titles == ["Morning", "Afternoon", "Evening"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_edge_pet_with_no_tasks_produces_empty_schedule():
    """A pet registered with zero tasks should not crash and yields an empty schedule."""
    owner = Owner(name="Alex", available_minutes=60)
    owner.add_pet(Pet(name="Ghost", species="cat", age=1))
    schedule = Scheduler(owner).generate()
    assert schedule.planned_tasks == []
    assert schedule.conflicts == []

def test_edge_two_tasks_at_exact_same_time_detected():
    """Two tasks pinned to the identical HH:MM time produce exactly one collision conflict."""
    owner = _make_owner_with_timed_tasks(
        ("Rex", [("Walk", "09:00"), ("Meds", "09:00")]),
    )
    schedule = Scheduler(owner).generate()
    collisions = [c for c in schedule.conflicts if "collision" in c.lower()]
    assert len(collisions) == 1
    assert "09:00" in collisions[0]

def test_edge_weekly_task_at_exact_7_day_boundary():
    """A weekly task last done exactly 7 days ago is due today (boundary is inclusive)."""
    task = Task(title="Bath", duration_minutes=20, priority="medium", category="grooming", frequency="weekly")
    task.last_completed_date = date.today() - timedelta(days=7)
    assert task.is_due_today() is True

def test_edge_complete_task_twice_completes_recurring_copy(sample_pet):
    """Calling complete_task a second time matches the pending recurring copy (same title).

    Known behaviour: complete_task searches by title, so the second call finds
    the recurring_copy appended by the first call and completes it, producing a
    second copy.  This test documents that behaviour; callers should guard
    against double-completing the same logical task.
    """
    sample_pet.complete_task("Morning walk")          # completes original → copy #1 added
    count_after_first = len(sample_pet.get_tasks())   # original + 3 tasks = 4
    sample_pet.complete_task("Morning walk")          # completes copy #1 → copy #2 added
    assert len(sample_pet.get_tasks()) == count_after_first + 1

def test_edge_undo_on_never_completed_task_is_noop(sample_pet):
    """undo_complete on a task that was never completed leaves the list unchanged."""
    count_before = len(sample_pet.get_tasks())
    sample_pet.undo_complete("Morning walk")
    assert len(sample_pet.get_tasks()) == count_before
    original = next(t for t in sample_pet.get_tasks() if t.title == "Morning walk")
    assert original.completed is False

def test_edge_budget_zero_yields_empty_schedule(sample_owner):
    """available_minutes=0 means no task can fit; schedule must be empty."""
    sample_owner.set_availability(0)
    schedule = Scheduler(sample_owner).generate()
    assert schedule.planned_tasks == []

def test_edge_recurring_copy_not_due_same_day(sample_pet):
    """The follow-up created by complete_task has a future due_date and is not due today."""
    sample_pet.complete_task("Morning walk")
    copies = [t for t in sample_pet.get_tasks() if t.recurring_copy]
    assert len(copies) == 1
    assert copies[0].is_due_today() is False

def test_edge_sort_by_time_untimed_tasks_go_last():
    """Tasks with no scheduled_time sort after all timed tasks."""
    owner = Owner(name="Test", available_minutes=120)
    scheduler = Scheduler(owner)
    pet = Pet(name="Buddy", species="dog", age=2)
    timed   = (pet, Task(title="Timed",   duration_minutes=5, priority="low", category="walk", scheduled_time="23:00"))
    untimed = (pet, Task(title="Untimed", duration_minutes=5, priority="low", category="walk", scheduled_time=""))
    result = scheduler.sort_by_time([untimed, timed])
    assert result[0][1].title == "Timed"
    assert result[1][1].title == "Untimed"
