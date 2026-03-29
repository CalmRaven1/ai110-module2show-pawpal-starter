from dataclasses import dataclass, field
from datetime import date as Date


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str           # "low", "medium", "high"
    category: str           # "walk", "feeding", "meds", "grooming", "enrichment"
    frequency: str = "daily"  # "daily", "weekly", "as-needed"
    completed: bool = False

    def mark_complete(self):
        """Mark this task as completed."""
        self.completed = True

    def reset(self):
        """Reset this task to incomplete so it can be rescheduled."""
        self.completed = False

    def is_urgent(self) -> bool:
        """Return True if this task has high priority."""
        return self.priority == "high"

    def __str__(self) -> str:
        """Return a readable one-line summary of this task."""
        status = "done" if self.completed else "pending"
        return f"[{self.priority.upper()}] {self.title} ({self.duration_minutes} min, {self.frequency}) — {status}"


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

    def __str__(self) -> str:
        """Return a readable one-line description of this pet."""
        return f"{self.name} ({self.species}, age {self.age})"


@dataclass
class Owner:
    name: str
    available_minutes: int
    preference: str = ""    # "morning", "evening", or ""
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


class Schedule:
    def __init__(self, date: Date):
        self.date = date
        self.planned_tasks: list[tuple[Pet, Task]] = []
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
            lines.append(f"- [{task.priority.upper()}] {pet.name}: {task.title} ({task.duration_minutes} min)")
        if self.explanation:
            lines.append(f"\nReasoning: {self.explanation}")
        return "\n".join(lines)


class Scheduler:
    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner):
        self.owner = owner

    def _collect_tasks(self) -> list[tuple[Pet, Task]]:
        """Retrieve all pending tasks from every pet the owner has."""
        return self.owner.get_all_pending_tasks()

    def generate(self) -> Schedule:
        """Build and return a Schedule by fitting pending tasks within the owner's time budget."""
        pending = self._collect_tasks()

        # Sort by priority; break ties by duration (shorter first)
        sorted_tasks = sorted(
            pending,
            key=lambda pt: (self.PRIORITY_ORDER.get(pt[1].priority, 2), pt[1].duration_minutes),
        )

        schedule = Schedule(date=Date.today())
        for pet, task in sorted_tasks:
            if schedule.total_duration + task.duration_minutes <= self.owner.available_minutes:
                schedule.add_task(pet, task)

        schedule.explanation = self._explain(schedule)
        return schedule

    def _explain(self, schedule: Schedule) -> str:
        """Generate a plain-text explanation of why tasks were selected or skipped."""
        if not schedule.planned_tasks:
            return "No tasks could fit within the available time."
        skipped = len(self._collect_tasks()) - len(schedule.planned_tasks)
        lines = [
            f"Scheduled {len(schedule.planned_tasks)} task(s) for {self.owner.name}'s pet(s), "
            f"fitting within {self.owner.available_minutes} available minutes."
        ]
        if skipped:
            lines.append(f"{skipped} task(s) were skipped due to time constraints.")
        return " ".join(lines)
