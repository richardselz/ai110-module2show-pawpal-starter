from datetime import date, timedelta
from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    TaskType, Priority, Frequency,
)

# --- Setup Owner ---
owner = Owner(id="o1", name="Alex", email="alex@example.com")

# --- Setup Pets ---
buddy = Pet(id="p1", name="Buddy", species="Dog", breed="Golden Retriever", birth_date=date(2020, 3, 15))
luna  = Pet(id="p2", name="Luna",  species="Cat", breed="Siamese",          birth_date=date(2022, 7, 4))

owner.pets = [buddy, luna]

# --- Setup Tasks ---
buddy.task_list = [
    Task(
        id="t1",
        type=TaskType.FEEDING,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=10),
        description="Morning feeding",
        due_date=date.today(),
    ),
    Task(
        id="t2",
        type=TaskType.EXERCISE,
        priority=Priority.MEDIUM,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=30),
        description="Morning walk around the block",
        due_date=date.today(),
    ),
]

luna.task_list = [
    Task(
        id="t3",
        type=TaskType.MEDICATION,
        priority=Priority.URGENT,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=5),
        description="Administer allergy medication",
        due_date=date.today(),
    ),
    Task(
        id="t4",
        type=TaskType.GROOMING,
        priority=Priority.LOW,
        frequency=Frequency.WEEKLY,
        time_for_task=timedelta(minutes=20),
        description="Brush coat",
        due_date=date.today(),
    ),
]

# --- Run Scheduler ---
scheduler = Scheduler(owner=owner)

print("=" * 40)
print("       TODAY'S SCHEDULE")
print(f"       {date.today().strftime('%A, %B %d %Y')}")
print("=" * 40)

for pet in owner.pets:
    print(f"\n{pet.name} ({pet.breed})")
    print("-" * 40)
    if not pet.task_list:
        print("  No tasks scheduled.")
        continue
    for task in pet.task_list:
        duration = int(task.time_for_task.total_seconds() // 60)
        print(f"  [{task.priority.name:<6}] {task.description}")
        print(f"           Type: {task.type.name}  |  Duration: {duration} min  |  Frequency: {task.frequency.name}")
        print(f"           Status: {task.status.name}")

print("\n" + "=" * 40)
