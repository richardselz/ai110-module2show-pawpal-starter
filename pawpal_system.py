from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, time, timedelta
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


# --- Dataclasses ---

@dataclass
class TimeConstraint:
    day_of_week: str          # e.g. "Monday", "Saturday"
    start_time: time
    end_time: time

    def is_available(self, check_time: time) -> bool:
        """Return True if check_time falls within this constraint's window."""
        return False


@dataclass
class Task:
    id: str
    type: TaskType
    priority: Priority
    time_for_task: timedelta
    description: str
    status: TaskStatus = TaskStatus.PENDING
    due_date: date | None = None

    def start(self) -> None:
        """Mark this task as in progress."""
        pass

    def complete(self) -> None:
        """Mark this task as completed."""
        pass

    def skip(self) -> None:
        """Mark this task as skipped."""
        pass


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
        pass

    def remove_task(self, task_id: str) -> None:
        """Remove a task by id from this pet's task list."""
        pass

    def get_pending_tasks(self) -> list[Task]:
        """Return all tasks with PENDING status."""
        return []

    def get_tasks_by_priority(self) -> list[Task]:
        """Return task list sorted by priority descending (URGENT first)."""
        return []


@dataclass
class Plan:
    id: str
    name: str
    start_date: date
    end_date: date
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this plan."""
        pass

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by id from this plan."""
        pass

    def get_all_tasks(self) -> list[Task]:
        """Return all tasks across every pet in this plan."""
        return []


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
        pass

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by id from the owner's roster."""
        pass

    def add_plan(self, plan: Plan) -> None:
        """Add a care plan for this owner."""
        pass

    def add_time_constraint(self, constraint: TimeConstraint) -> None:
        """Add an availability window for this owner."""
        pass

    def get_available_times(self, day_of_week: str) -> list[TimeConstraint]:
        """Return all time constraints for a given day."""
        return []
