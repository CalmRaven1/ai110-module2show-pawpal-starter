from dataclasses import dataclass, field
from datetime import date as Date


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str        # "low", "medium", "high"
    category: str        # "walk", "feeding", "meds", "grooming", "enrichment"
    completed: bool = False

    def mark_complete(self):
        self.completed = True

    def is_urgent(self) -> bool:
        return self.priority == "high"


@dataclass
class Pet:
    name: str
    species: str
    age: int
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def get_tasks(self) -> list[Task]:
        return self.tasks


@dataclass
class Owner:
    name: str
    available_minutes: int
    preference: str = ""  # e.g. "morning", "evening"
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet):
        self.pets.append(pet)

    def set_availability(self, minutes: int):
        self.available_minutes = minutes


class Schedule:
    def __init__(self, date: Date):
        self.date = date
        self.planned_tasks: list[Task] = []
        self.total_duration: int = 0
        self.explanation: str = ""

    def add_task(self, task: Task):
        self.planned_tasks.append(task)
        self.total_duration += task.duration_minutes

    def remove_task(self, task: Task):
        if task in self.planned_tasks:
            self.planned_tasks.remove(task)
            self.total_duration -= task.duration_minutes

    def get_summary(self) -> str:
        lines = [f"Schedule for {self.date}", f"Total time: {self.total_duration} min", ""]
        for task in self.planned_tasks:
            lines.append(f"- [{task.priority.upper()}] {task.title} ({task.duration_minutes} min)")
        if self.explanation:
            lines.append(f"\nReasoning: {self.explanation}")
        return "\n".join(lines)


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner

    def generate(self, tasks: list[Task], available_minutes: int) -> Schedule:
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_tasks = sorted(tasks, key=lambda t: priority_order.get(t.priority, 2))

        schedule = Schedule(date=Date.today())
        time_used = 0

        for task in sorted_tasks:
            if time_used + task.duration_minutes <= available_minutes:
                schedule.add_task(task)
                time_used += task.duration_minutes

        schedule.explanation = self.explain(schedule.planned_tasks, available_minutes)
        return schedule

    def explain(self, planned_tasks: list[Task], available_minutes: int) -> str:
        if not planned_tasks:
            return "No tasks could fit within the available time."
        names = ", ".join(t.title for t in planned_tasks)
        return (
            f"Selected {len(planned_tasks)} task(s) ({names}) "
            f"ordered by priority to fit within {available_minutes} minutes."
        )
