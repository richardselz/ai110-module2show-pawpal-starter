from datetime import date, timedelta
from pawpal_system import Pet, Task, TaskType, Priority, TaskStatus, Frequency


def make_task(task_id: str = "t1") -> Task:
    return Task(
        id=task_id,
        type=TaskType.FEEDING,
        priority=Priority.MEDIUM,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=10),
        description="Test task",
        due_date=date.today(),
    )


def test_task_complete_changes_status():
    task = make_task()
    assert task.status == TaskStatus.PENDING
    task.complete()
    assert task.status == TaskStatus.COMPLETED


def test_add_task_increases_pet_task_count():
    pet = Pet(id="p1", name="Buddy", species="Dog", breed="Labrador", birth_date=date(2020, 1, 1))
    assert len(pet.task_list) == 0
    pet.add_task(make_task("t1"))
    pet.add_task(make_task("t2"))
    assert len(pet.task_list) == 2
