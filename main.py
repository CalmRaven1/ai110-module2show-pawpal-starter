from pawpal_system import Owner, Pet, Task, Scheduler

# --- Create Owner ---
owner = Owner(name="Jordan", available_minutes=90, preference="morning")

# --- Create Pet 1: Mochi the dog ---
mochi = Pet(name="Mochi", species="dog", age=3)
mochi.add_task(Task(title="Morning walk",  duration_minutes=20, priority="high",   category="walk"))
mochi.add_task(Task(title="Breakfast",     duration_minutes=5,  priority="high",   category="feeding"))
mochi.add_task(Task(title="Puzzle toy",    duration_minutes=15, priority="low",    category="enrichment"))

# --- Create Pet 2: Luna the cat ---
luna = Pet(name="Luna", species="cat", age=5)
luna.add_task(Task(title="Flea medicine",  duration_minutes=5,  priority="high",   category="meds"))
luna.add_task(Task(title="Brush coat",     duration_minutes=10, priority="medium", category="grooming"))
luna.add_task(Task(title="Dinner",         duration_minutes=5,  priority="high",   category="feeding"))

owner.add_pet(mochi)
owner.add_pet(luna)

# --- Generate and print schedule ---
scheduler = Scheduler(owner)
schedule = scheduler.generate()

PRIORITY_ICON = {"high": "(!)", "medium": "(~)", "low": "( )"}

print()
print("=" * 44)
print(f"  PawPal+ | Today's Schedule  ({schedule.date})")
print(f"  Owner: {owner.name}  |  Budget: {owner.available_minutes} min")
print("=" * 44)

for pet, task in schedule.planned_tasks:
    icon = PRIORITY_ICON.get(task.priority, "   ")
    print(f"  {icon}  {task.title:<22} {task.duration_minutes:>3} min  [{pet.name}]")

print("-" * 44)
print(f"  Total: {schedule.total_duration} min used / {owner.available_minutes} min available")
print()
print(f"  Note: {schedule.explanation}")
print("=" * 44)
print()
