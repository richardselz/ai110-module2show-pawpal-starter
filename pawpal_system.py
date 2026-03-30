from __future__ import annotations
import copy
import uuid
from dataclasses import dataclass, field
from datetime import date, time, timedelta, datetime
from enum import Enum


# --- Enumerations ---

class TaskType(Enum):
    FEEDING = "feeding"
    GROOMING = "grooming"
    EXERCISE = "exercise"
    VET_VISIT = "vet_visit"
    MEDICATION = "medication"
    TRAINING = "training"
    OTHER = "other"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# --- Dataclasses ---

@dataclass
class TimeConstraint:
    day_of_week: str          # e.g. "Monday", "Saturday"
    start_time: time
    end_time: time

    def is_available(self, check_time: time) -> bool:
        """Return True if check_time falls within this constraint's window."""
        return self.start_time <= check_time <= self.end_time


@dataclass
class Task:
    id: str
    type: TaskType
    priority: Priority
    time_for_task: timedelta
    description: str
    frequency: Frequency = Frequency.ONCE
    status: TaskStatus = TaskStatus.PENDING
    due_date: date | None = None
    scheduled_time: str | None = None  # "HH:MM" format, e.g. "08:30"

    def start(self) -> None:
        """Mark this task as in progress."""
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        """Mark this task as completed."""
        self.status = TaskStatus.COMPLETED

    def skip(self) -> None:
        """Mark this task as skipped."""
        self.status = TaskStatus.SKIPPED

    def next_due_date(self) -> date | None:
        """Return the next occurrence date based on frequency, or None if non-recurring."""
        if not self.due_date or self.frequency == Frequency.ONCE:
            return None
        delta_map = {
            Frequency.DAILY: timedelta(days=1),
            Frequency.WEEKLY: timedelta(weeks=1),
            Frequency.MONTHLY: timedelta(days=30),
        }
        return self.due_date + delta_map[self.frequency]


@dataclass
class Pet:
    id: str
    name: str
    species: str
    breed: str
    birth_date: date
    task_list: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.task_list.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by id from this pet's task list."""
        self.task_list = [t for t in self.task_list if t.id != task_id]

    def get_pending_tasks(self) -> list[Task]:
        """Return all tasks with PENDING status."""
        return [t for t in self.task_list if t.status == TaskStatus.PENDING]

    def get_tasks_by_priority(self) -> list[Task]:
        """Return task list sorted by priority descending (URGENT first)."""
        return sorted(self.task_list, key=lambda t: t.priority.value, reverse=True)


@dataclass
class Plan:
    id: str
    name: str
    start_date: date
    end_date: date
    pet_ids: list[str] = field(default_factory=list)

    def add_pet(self, pet_id: str) -> None:
        """Add a pet by id to this plan."""
        if pet_id not in self.pet_ids:
            self.pet_ids.append(pet_id)

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by id from this plan."""
        self.pet_ids = [p for p in self.pet_ids if p != pet_id]

    def get_all_tasks(self, pet_lookup: dict[str, Pet]) -> list[Task]:
        """Return all tasks across every pet in this plan using a pet_id-to-Pet lookup dict."""
        return [
            task
            for pid in self.pet_ids
            if pid in pet_lookup
            for task in pet_lookup[pid].task_list
        ]


@dataclass
class Owner:
    id: str
    name: str
    email: str
    pets: list[Pet] = field(default_factory=list)
    plans: list[Plan] = field(default_factory=list)
    time_constraints: list[TimeConstraint] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's roster."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by id from the owner's roster."""
        self.pets = [p for p in self.pets if p.id != pet_id]

    def add_plan(self, plan: Plan) -> None:
        """Add a care plan for this owner."""
        self.plans.append(plan)

    def add_time_constraint(self, constraint: TimeConstraint) -> None:
        """Add an availability window for this owner."""
        self.time_constraints.append(constraint)

    def get_available_times(self, day_of_week: str) -> list[TimeConstraint]:
        """Return all time constraints for a given day."""
        return [c for c in self.time_constraints if c.day_of_week == day_of_week]

    def get_all_tasks(self) -> list[Task]:
        """Return a flat list of all tasks across all owned pets."""
        return [task for pet in self.pets for task in pet.task_list]


@dataclass
class Scheduler:
    owner: Owner

    def get_all_tasks(self) -> list[Task]:
        """Retrieve a flat list of every task across all of the owner's pets."""
        return self.owner.get_all_tasks()

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks with PENDING status."""
        return [t for t in self.get_all_tasks() if t.status == TaskStatus.PENDING]

    def get_tasks_by_priority(self) -> list[Task]:
        """Return all pending tasks sorted by priority descending (URGENT first)."""
        return sorted(self.get_pending_tasks(), key=lambda t: t.priority.value, reverse=True)

    def get_tasks_by_pet(self) -> dict[str, list[Task]]:
        """Return tasks grouped by pet name."""
        return {pet.name: pet.task_list for pet in self.owner.pets}

    # --- Phase 4: Algorithmic Layer ---

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """
        Return tasks sorted by scheduled_time in ascending HH:MM order.
        Tasks without a scheduled_time are placed at the end.
        Uses a lambda with a sentinel value so Python's sorted() can compare strings directly.
        """
        source = tasks if tasks is not None else self.get_all_tasks()
        return sorted(source, key=lambda t: t.scheduled_time or "99:99")

    def filter_tasks(
        self,
        pet_name: str | None = None,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        """
        Return tasks filtered by pet name and/or completion status.
        Either filter is optional — pass neither to get all tasks.
        Matching is case-insensitive for pet names.
        """
        results: list[Task] = []
        for pet in self.owner.pets:
            if pet_name and pet.name.lower() != pet_name.lower():
                continue
            for task in pet.task_list:
                if status and task.status != status:
                    continue
                results.append(task)
        return results

    def complete_task(self, task: Task, pet: Pet) -> Task | None:
        """
        Mark a task complete. For recurring tasks (DAILY / WEEKLY / MONTHLY), automatically
        create the next occurrence and add it to the pet's task list.
        Returns the new Task instance, or None if the task was a one-time task.
        """
        task.complete()
        next_date = task.next_due_date()
        if next_date is None:
            return None
        # Shallow-copy preserves all fields; we only update identity, status, and due date.
        new_task = copy.copy(task)
        new_task.id = str(uuid.uuid4())
        new_task.status = TaskStatus.PENDING
        new_task.due_date = next_date
        pet.add_task(new_task)
        return new_task

    def detect_conflicts(self, tasks: list[Task] | None = None) -> list[str]:
        """
        Detect scheduling conflicts among tasks that have a scheduled_time set.
        Two tasks conflict when their time windows overlap (start-to-start + duration).
        Returns a list of human-readable warning strings; empty list means no conflicts.
        O(n log n + k) where k = number of actual conflicts: sort once by start time,
        then break the inner loop as soon as b.start >= a.end (no further overlap possible).
        """
        active = {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}
        source = [
            t for t in (tasks or self.get_all_tasks())
            if t.scheduled_time and t.status in active
        ]

        # Sort once by start time so the early-exit break is valid
        source.sort(key=lambda t: t.scheduled_time)

        warnings: list[str] = []

        for i, a in enumerate(source):
            a_start = datetime.strptime(a.scheduled_time, "%H:%M")  # type: ignore[arg-type]
            a_end = a_start + a.time_for_task

            for b in source[i + 1:]:
                b_start = datetime.strptime(b.scheduled_time, "%H:%M")  # type: ignore[arg-type]
                if b_start >= a_end:
                    break  # sorted, so nothing further can overlap with a
                b_end = b_start + b.time_for_task
                warnings.append(
                    f"WARNING: '{a.description}' "
                    f"({a.scheduled_time}-{a_end.strftime('%H:%M')}) "
                    f"overlaps with '{b.description}' "
                    f"({b.scheduled_time}-{b_end.strftime('%H:%M')})"
                )

        return warnings

    def schedule(self) -> list[Task]:
        """
        Build an ordered daily schedule:
        1. Pending tasks with a scheduled_time are sorted chronologically.
        2. Pending tasks without a scheduled_time follow, ordered by priority.
        """
        pending = self.get_tasks_by_priority()
        timed = [t for t in pending if t.scheduled_time]
        untimed = [t for t in pending if not t.scheduled_time]
        return self.sort_by_time(timed) + untimed
