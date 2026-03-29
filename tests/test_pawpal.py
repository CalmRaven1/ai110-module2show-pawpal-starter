import pytest
from pawpal_system import Owner, Pet, Task, Scheduler


# --- Fixtures ---

@pytest.fixture
def sample_pet():
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task(title="Morning walk",  duration_minutes=20, priority="high",   category="walk"))
    pet.add_task(Task(title="Breakfast",     duration_minutes=5,  priority="high",   category="feeding"))
    pet.add_task(Task(title="Puzzle toy",    duration_minutes=15, priority="low",    category="enrichment"))
    return pet


@pytest.fixture
def sample_owner(sample_pet):
    owner = Owner(name="Jordan", available_minutes=90, preference="morning")
    owner.add_pet(sample_pet)
    return owner


# --- Task tests ---

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

def test_task_reset():
    task = Task(title="Walk", duration_minutes=20, priority="medium", category="walk")
    task.mark_complete()
    task.reset()
    assert task.completed is False


# --- Pet tests ---

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


# --- Owner tests ---

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


# --- Scheduler tests ---

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
