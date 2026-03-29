from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler

PRIORITY_ICON = {"high": "(!)", "medium": "(~)", "low": "( )"}
SLOT_ICON = {"morning": "[AM]", "afternoon": "[PM]", "evening": "[EVE]", "anytime": "[ANY]"}


def print_schedule(owner, schedule):
    print()
    print("=" * 52)
    print(f"  PawPal+ | Today's Schedule  ({schedule.date})")
    print(f"  Owner: {owner.name}  |  Budget: {owner.available_minutes} min")
    print("=" * 52)
    if not schedule.planned_tasks:
        print("  No tasks scheduled.")
    for pet, task in schedule.planned_tasks:
        icon = PRIORITY_ICON.get(task.priority, "   ")
        slot = SLOT_ICON.get(task.time_slot, "[ANY]")
        print(f"  {icon} {slot}  {task.title:<22} {task.duration_minutes:>3} min  [{pet.name}]")
    print("-" * 52)
    print(f"  Total: {schedule.total_duration} min used / {owner.available_minutes} min available")
    if schedule.conflicts:
        for c in schedule.conflicts:
            print(f"  !! CONFLICT: {c}")
    print(f"  Note: {schedule.explanation}")
    print("=" * 52)
    print()


# ── Scenario 1: Happy path ────────────────────────────────
print("\n>>> Scenario 1: Normal day, sorted by slot then priority")

owner = Owner(name="Jordan", available_minutes=90, preference="morning")

mochi = Pet(name="Mochi", species="dog", age=3)
mochi.add_task(Task(title="Morning walk",  duration_minutes=20, priority="high",   category="walk",      time_slot="morning"))
mochi.add_task(Task(title="Breakfast",     duration_minutes=5,  priority="high",   category="feeding",   time_slot="morning"))
mochi.add_task(Task(title="Puzzle toy",    duration_minutes=15, priority="low",    category="enrichment",time_slot="afternoon"))

luna = Pet(name="Luna", species="cat", age=5)
luna.add_task(Task(title="Flea medicine",  duration_minutes=5,  priority="high",   category="meds",      time_slot="morning"))
luna.add_task(Task(title="Brush coat",     duration_minutes=10, priority="medium", category="grooming",  time_slot="evening"))
luna.add_task(Task(title="Dinner",         duration_minutes=5,  priority="high",   category="feeding",   time_slot="evening"))

owner.add_pet(mochi)
owner.add_pet(luna)

print_schedule(owner, Scheduler(owner).generate())


# ── Scenario 2: Tight budget — low-priority tasks dropped ─
print(">>> Scenario 2: Tight budget (25 min), low-priority tasks should be skipped")

owner.set_availability(25)
print_schedule(owner, Scheduler(owner).generate())


# ── Scenario 3: Completed tasks excluded ──────────────────
print(">>> Scenario 3: Mark 'Morning walk' complete — should not appear in schedule")

owner.set_availability(90)
mochi.get_tasks()[0].mark_complete()
print_schedule(owner, Scheduler(owner).generate())

mochi.get_tasks()[0].reset()


# ── Scenario 4: No tasks at all ───────────────────────────
print(">>> Scenario 4: Pet with no tasks — schedule should be empty")

empty_owner = Owner(name="Alex", available_minutes=60)
empty_owner.add_pet(Pet(name="Ghost", species="cat", age=1))
print_schedule(empty_owner, Scheduler(empty_owner).generate())


# ── Scenario 5: Remove a pet ──────────────────────────────
print(">>> Scenario 5: Remove Luna — only Mochi's tasks should appear")

owner.set_availability(90)
owner.remove_pet("Luna")
print_schedule(owner, Scheduler(owner).generate())
owner.add_pet(luna)   # restore for later scenarios


# ── Scenario 6: Recurring tasks (weekly) ─────────────────
print(">>> Scenario 6: Weekly task done recently — should not appear in schedule")

rex = Pet(name="Rex", species="dog", age=4)
# Completed 2 days ago — not due yet
weekly_bath = Task(title="Bath", duration_minutes=30, priority="medium",
                   category="grooming", frequency="weekly", time_slot="morning")
weekly_bath.completed = True
weekly_bath.last_completed_date = date.today() - timedelta(days=2)
rex.add_task(weekly_bath)

# Completed 8 days ago — due again
weekly_nails = Task(title="Nail trim", duration_minutes=10, priority="low",
                    category="grooming", frequency="weekly", time_slot="afternoon")
weekly_nails.completed = True
weekly_nails.last_completed_date = date.today() - timedelta(days=8)
weekly_nails.completed = False   # reset the flag; last_completed_date stays for due check
rex.add_task(weekly_nails)

recurring_owner = Owner(name="Sam", available_minutes=60)
recurring_owner.add_pet(rex)
schedule6 = Scheduler(recurring_owner).generate()
print_schedule(recurring_owner, schedule6)
# Expect: Bath skipped (not due), Nail trim scheduled (overdue)


# ── Scenario 7: filter_tasks ──────────────────────────────
print(">>> Scenario 7: filter_tasks — pending only for Mochi")

owner.set_availability(90)
mochi.get_tasks()[1].mark_complete()   # mark Breakfast complete

pending_mochi = owner.filter_tasks(pet_name="Mochi", status="pending")
print(f"  Pending tasks for Mochi: {[t.title for _, t in pending_mochi]}")

all_completed = owner.filter_tasks(status="completed")
print(f"  All completed tasks: {[t.title for _, t in all_completed]}")

mochi.get_tasks()[1].reset()   # restore


# ── Scenario 9: sort_by_time + filter_tasks ──────────────
print(">>> Scenario 9: Tasks added out of order — sort_by_time and filter_tasks")

sort_owner = Owner(name="Riley", available_minutes=180)

pip = Pet(name="Pip", species="dog", age=2)
# Added deliberately out of chronological order
pip.add_task(Task(title="Evening walk",  duration_minutes=25, priority="medium", category="walk",        scheduled_time="18:00"))
pip.add_task(Task(title="Breakfast",     duration_minutes=5,  priority="high",   category="feeding",     scheduled_time="07:00"))
pip.add_task(Task(title="Lunch snack",   duration_minutes=5,  priority="medium", category="feeding",     scheduled_time="12:30"))
pip.add_task(Task(title="Morning walk",  duration_minutes=20, priority="high",   category="walk",        scheduled_time="07:45"))
pip.add_task(Task(title="Flea meds",     duration_minutes=5,  priority="high",   category="meds",        scheduled_time="09:00"))

noodle = Pet(name="Noodle", species="cat", age=4)
noodle.add_task(Task(title="Dinner",       duration_minutes=5,  priority="high",   category="feeding",   scheduled_time="17:30"))
noodle.add_task(Task(title="Brush coat",   duration_minutes=10, priority="low",    category="grooming",  scheduled_time="10:00"))
noodle.add_task(Task(title="Play session", duration_minutes=15, priority="medium", category="enrichment",scheduled_time="15:00"))

sort_owner.add_pet(pip)
sort_owner.add_pet(noodle)

# mark one task complete so filtering has something to show
pip.get_tasks()[2].mark_complete()   # Lunch snack → completed

scheduler9 = Scheduler(sort_owner)
all_tasks = sort_owner.get_all_tasks()

print("\n  -- All tasks as added (unsorted) --")
for p, t in all_tasks:
    done = " [done]" if t.completed else ""
    print(f"    {t.scheduled_time or '??:??'}  {p.name:<8} {t.title}{done}")

print("\n  -- All tasks sorted by scheduled_time --")
for p, t in scheduler9.sort_by_time(all_tasks):
    done = " [done]" if t.completed else ""
    print(f"    {t.scheduled_time or '(none)'}  {p.name:<8} {t.title}{done}")

print("\n  -- Pending tasks only, sorted by time --")
pending = scheduler9.filter_tasks(all_tasks, status="pending")
for p, t in scheduler9.sort_by_time(pending):
    print(f"    {t.scheduled_time or '(none)'}  {p.name:<8} {t.title}")

print("\n  -- Completed tasks only --")
completed = scheduler9.filter_tasks(all_tasks, status="completed")
for p, t in completed:
    print(f"    {t.scheduled_time or '(none)'}  {p.name:<8} {t.title}")

print("\n  -- Pip's tasks only, sorted by time --")
pip_tasks = scheduler9.filter_tasks(all_tasks, pet_name="Pip")
for p, t in scheduler9.sort_by_time(pip_tasks):
    done = " [done]" if t.completed else ""
    print(f"    {t.scheduled_time or '(none)'}  {p.name:<8} {t.title}{done}")

print("\n  -- Noodle's pending tasks, sorted by time --")
noodle_pending = scheduler9.filter_tasks(all_tasks, pet_name="Noodle", status="pending")
for p, t in scheduler9.sort_by_time(noodle_pending):
    print(f"    {t.scheduled_time or '(none)'}  {p.name:<8} {t.title}")

print()


# ── Scenario 10: Auto-recurrence on complete ─────────────
print(">>> Scenario 10: complete_task() auto-creates next occurrence; undo removes it")

recur_owner = Owner(name="Dana", available_minutes=120)
bolt = Pet(name="Bolt", species="dog", age=2)
bolt.add_task(Task(title="Morning walk", duration_minutes=20, priority="high",
                   category="walk", frequency="daily", scheduled_time="07:30"))
bolt.add_task(Task(title="Bath",         duration_minutes=30, priority="medium",
                   category="grooming", frequency="weekly", scheduled_time="10:00"))
bolt.add_task(Task(title="Vet visit",    duration_minutes=60, priority="high",
                   category="meds", frequency="as-needed", scheduled_time="14:00"))
recur_owner.add_pet(bolt)

def show_tasks(label):
    print(f"\n  {label}")
    for t in bolt.get_tasks():
        flag = f" [recurring copy — due {t.due_date}]" if t.recurring_copy else ""
        done = " [done]" if t.completed else ""
        print(f"    {t.scheduled_time or '??:??'}  [{t.frequency:<9}]  {t.title}{done}{flag}")

show_tasks("Before completing anything:")

bolt.complete_task("Morning walk")   # daily  → follow-up created
bolt.complete_task("Bath")           # weekly → follow-up created
bolt.complete_task("Vet visit")      # as-needed → NO follow-up

show_tasks("After completing all three:")

print("\n  Undoing 'Morning walk' — its recurring copy should disappear:")
bolt.undo_complete("Morning walk")
show_tasks("After undo:")

print()


# ── Scenario 8: Conflict detection ───────────────────────
print(">>> Scenario 8: Conflict detection — morning slot overbooked")

big_owner = Owner(name="Casey", available_minutes=480)
buddy = Pet(name="Buddy", species="dog", age=2)
# Stack many long tasks in morning to exceed 120-min slot capacity
for i in range(1, 6):
    buddy.add_task(Task(
        title=f"Morning task {i}",
        duration_minutes=30,
        priority="high",
        category="walk",
        time_slot="morning",
    ))
big_owner.add_pet(buddy)
schedule8 = Scheduler(big_owner).generate()
print_schedule(big_owner, schedule8)
# Expect: morning slot overbooked conflict + duplicate 'walk' category conflicts


# ── Scenario 11: Exact time collision detection ───────────
print(">>> Scenario 11: Exact scheduled_time collisions (same pet and cross-pet)")

clash_owner = Owner(name="Morgan", available_minutes=240)

rex = Pet(name="Rex", species="dog", age=3)
# Two tasks for Rex at the same time → same-pet collision
rex.add_task(Task(title="Morning walk", duration_minutes=20, priority="high",
                  category="walk",    scheduled_time="08:00"))
rex.add_task(Task(title="Breakfast",   duration_minutes=5,  priority="high",
                  category="feeding", scheduled_time="08:00"))

cleo = Pet(name="Cleo", species="cat", age=4)
# One task for Cleo at the same time as Rex's walk → cross-pet collision
cleo.add_task(Task(title="Flea meds",   duration_minutes=5,  priority="high",
                   category="meds",    scheduled_time="08:00"))
# A task with a unique time — no collision expected
cleo.add_task(Task(title="Brush coat",  duration_minutes=10, priority="medium",
                   category="grooming",scheduled_time="10:30"))

clash_owner.add_pet(rex)
clash_owner.add_pet(cleo)

schedule11 = Scheduler(clash_owner).generate()
print_schedule(clash_owner, schedule11)
# Expect: same-pet collision (Rex at 08:00) and cross-pet collision (Rex + Cleo at 08:00)


# ── Scenario 12: Same-time collision — minimal, explicit ─────────────────
print(">>> Scenario 12a: Same-pet — two tasks pinned to 09:00")

owner_12a = Owner(name="Taylor", available_minutes=120)
dog = Pet(name="Biscuit", species="dog", age=2)
dog.add_task(Task(title="Morning walk", duration_minutes=20, priority="high",
                  category="walk",    scheduled_time="09:00"))
dog.add_task(Task(title="Flea meds",   duration_minutes=5,  priority="high",
                  category="meds",    scheduled_time="09:00"))   # ← same time
owner_12a.add_pet(dog)

schedule_12a = Scheduler(owner_12a).generate()
print_schedule(owner_12a, schedule_12a)

print("  Warnings detected:")
warnings_12a = [c for c in schedule_12a.conflicts if "collision" in c.lower()]
for w in warnings_12a:
    print(f"  ⚠  {w}")
print(f"  ({len(warnings_12a)} collision warning(s) found)\n")


print(">>> Scenario 12b: Cross-pet — two different pets both scheduled at 14:00")

owner_12b = Owner(name="Taylor", available_minutes=120)
cat1 = Pet(name="Mochi", species="cat", age=3)
cat2 = Pet(name="Noodle", species="cat", age=5)
cat1.add_task(Task(title="Afternoon meds",  duration_minutes=5,  priority="high",
                   category="meds",    scheduled_time="14:00"))
cat2.add_task(Task(title="Grooming session", duration_minutes=15, priority="medium",
                   category="grooming", scheduled_time="14:00"))  # ← same time, different pet
owner_12b.add_pet(cat1)
owner_12b.add_pet(cat2)

schedule_12b = Scheduler(owner_12b).generate()
print_schedule(owner_12b, schedule_12b)

print("  Warnings detected:")
warnings_12b = [c for c in schedule_12b.conflicts if "collision" in c.lower()]
for w in warnings_12b:
    print(f"  ⚠  {w}")
print(f"  ({len(warnings_12b)} collision warning(s) found)\n")


print(">>> Scenario 12c: No collision — tasks at different times (control case)")

owner_12c = Owner(name="Taylor", available_minutes=120)
dog2 = Pet(name="Biscuit", species="dog", age=2)
dog2.add_task(Task(title="Morning walk", duration_minutes=20, priority="high",
                   category="walk", scheduled_time="09:00"))
dog2.add_task(Task(title="Flea meds",   duration_minutes=5,  priority="high",
                   category="meds", scheduled_time="09:30"))  # ← different time, no clash
owner_12c.add_pet(dog2)

schedule_12c = Scheduler(owner_12c).generate()
print_schedule(owner_12c, schedule_12c)

print("  Warnings detected:")
warnings_12c = [c for c in schedule_12c.conflicts if "collision" in c.lower()]
for w in warnings_12c:
    print(f"  ⚠  {w}")
print(f"  ({len(warnings_12c)} collision warning(s) found — expected 0)\n")
