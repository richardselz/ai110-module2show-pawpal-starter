from datetime import date, timedelta
from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    TaskType, Priority, Frequency, TaskStatus,
)

# ── Setup ────────────────────────────────────────────────────────────────────
owner = Owner(id="o1", name="Alex", email="alex@example.com")

buddy = Pet(id="p1", name="Buddy", species="Dog", breed="Golden Retriever",
            birth_date=date(2020, 3, 15))
luna  = Pet(id="p2", name="Luna",  species="Cat", breed="Siamese",
            birth_date=date(2022, 7, 4))

owner.pets = [buddy, luna]

# Tasks added OUT OF ORDER on purpose so sorting is visible
buddy.task_list = [
    Task(
        id="t2",
        type=TaskType.EXERCISE,
        priority=Priority.MEDIUM,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=30),
        description="Morning walk around the block",
        due_date=date.today(),
        scheduled_time="08:00",   # added second but earlier in the day
    ),
    Task(
        id="t1",
        type=TaskType.FEEDING,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=10),
        description="Morning feeding",
        due_date=date.today(),
        scheduled_time="07:00",   # added first but displayed first after sort
    ),
]

luna.task_list = [
    Task(
        id="t4",
        type=TaskType.GROOMING,
        priority=Priority.LOW,
        frequency=Frequency.WEEKLY,
        time_for_task=timedelta(minutes=20),
        description="Brush coat",
        due_date=date.today(),
        scheduled_time="10:00",
    ),
    Task(
        id="t3",
        type=TaskType.MEDICATION,
        priority=Priority.URGENT,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=5),
        description="Administer allergy medication",
        due_date=date.today(),
        scheduled_time="07:30",
    ),
    # ── Step 4: two tasks that conflict with t3 (07:30–07:35) ────────────────
    Task(
        id="t5",
        type=TaskType.FEEDING,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
        time_for_task=timedelta(minutes=10),
        description="Luna morning feeding",
        due_date=date.today(),
        scheduled_time="07:32",   # starts inside t3's window → conflict
    ),
]

scheduler = Scheduler(owner=owner)

# ── Step 2a: Sort by time ─────────────────────────────────────────────────────
print("=" * 50)
print("  STEP 2a — SORTED BY SCHEDULED TIME")
print("=" * 50)
for task in scheduler.sort_by_time():
    print(f"  {task.scheduled_time or '??:??'}  [{task.priority.name:<6}]  {task.description}")

# ── Step 2b: Filter by pet ────────────────────────────────────────────────────
print()
print("=" * 50)
print("  STEP 2b — FILTER: only Buddy's tasks")
print("=" * 50)
for task in scheduler.filter_tasks(pet_name="Buddy"):
    print(f"  [{task.status.name}]  {task.description}")

# ── Step 2c: Filter by status ─────────────────────────────────────────────────
print()
print("=" * 50)
print("  STEP 2c — FILTER: only PENDING tasks")
print("=" * 50)
for task in scheduler.filter_tasks(status=TaskStatus.PENDING):
    print(f"  [{task.priority.name:<6}]  {task.description}")

# ── Step 3: Recurring task completion ─────────────────────────────────────────
print()
print("=" * 50)
print("  STEP 3 — RECURRING TASK COMPLETION")
print("=" * 50)
medication = luna.task_list[1]  # t3 — DAILY medication
print(f"  Completing: '{medication.description}'  (frequency={medication.frequency.name})")
print(f"  Due date before: {medication.due_date}")

new_task = scheduler.complete_task(medication, luna)

print(f"  Status after:    {medication.status.name}")
if new_task:
    print(f"  Next occurrence: '{new_task.description}'  due {new_task.due_date}  [{new_task.status.name}]")

luna_tasks_after = len(luna.task_list)
print(f"  Luna now has {luna_tasks_after} tasks (was 3 — new occurrence added automatically)")

# ── Step 4: Conflict detection ────────────────────────────────────────────────
print()
print("=" * 50)
print("  STEP 4 — CONFLICT DETECTION")
print("=" * 50)
conflicts = scheduler.detect_conflicts()
if conflicts:
    for warning in conflicts:
        print(f"  {warning}")
else:
    print("  No conflicts detected.")

# ── Full schedule (priority + time ordered) ───────────────────────────────────
print()
print("=" * 50)
print(f"  TODAY'S SCHEDULE — {date.today().strftime('%A, %B %d %Y')}")
print("=" * 50)
for task in scheduler.schedule():
    duration = int(task.time_for_task.total_seconds() // 60)
    print(f"  {task.scheduled_time or '--:--'}  [{task.priority.name:<6}]  {task.description}"
          f"  ({duration} min, {task.frequency.name})")
