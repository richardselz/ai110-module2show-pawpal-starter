import uuid
import streamlit as st
from datetime import date, timedelta
from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    TaskType, Priority, TaskStatus, Frequency,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(id=str(uuid.uuid4()), name="", email="")

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Sidebar — owner & pet setup
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Owner & Pet Setup")

    owner_name = st.text_input("Owner name", value=owner.name or "Jordan")
    owner.name = owner_name

    st.divider()
    st.subheader("Add a Pet")

    pet_name = st.text_input("Pet name", value="Mochi")
    species  = st.selectbox("Species", ["dog", "cat", "rabbit", "hamster",
                                        "parrot", "fish", "turtle", "snake",
                                        "guinea pig", "ferret", "other"])
    breed    = st.text_input("Breed (optional)", value="")

    if st.button("Add Pet", use_container_width=True):
        existing = next((p for p in owner.pets if p.name.lower() == pet_name.lower()), None)
        if existing:
            st.warning(f"A pet named **{pet_name}** already exists.")
        elif not pet_name.strip():
            st.warning("Please enter a pet name.")
        else:
            owner.add_pet(Pet(
                id=str(uuid.uuid4()),
                name=pet_name,
                species=species,
                breed=breed,
                birth_date=date.today(),
            ))
            st.success(f"**{pet_name}** added!")

    if owner.pets:
        st.divider()
        st.subheader("Remove a Pet")
        remove_name = st.selectbox("Select pet to remove",
                                   [p.name for p in owner.pets],
                                   key="remove_select")
        if st.button("Remove Pet", use_container_width=True):
            pet_to_remove = next(p for p in owner.pets if p.name == remove_name)
            owner.remove_pet(pet_to_remove.id)
            st.success(f"**{remove_name}** removed.")
            st.rerun()

# ---------------------------------------------------------------------------
# Main area — two columns
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1], gap="large")

# ── LEFT: Add a task ────────────────────────────────────────────────────────
with left:
    st.subheader("Add a Task")

    if not owner.pets:
        st.info("Add a pet in the sidebar first.")
    else:
        target_pet = st.selectbox("For pet", [p.name for p in owner.pets])
        task_title = st.text_input("Task description", value="Morning walk")

        col1, col2 = st.columns(2)
        with col1:
            task_type = st.selectbox("Type", [t.value for t in TaskType])
            priority  = st.selectbox("Priority",
                                     ["low", "medium", "high", "urgent"],
                                     index=2)
            frequency = st.selectbox("Frequency",
                                     ["once", "daily", "weekly", "monthly"])
        with col2:
            duration       = st.number_input("Duration (min)", min_value=1,
                                             max_value=480, value=20)
            scheduled_time = st.text_input("Scheduled time (HH:MM, optional)",
                                           placeholder="08:30")
            due_date       = st.date_input("Due date", value=date.today())

        _priority_map = {
            "low": Priority.LOW, "medium": Priority.MEDIUM,
            "high": Priority.HIGH, "urgent": Priority.URGENT,
        }
        _freq_map = {
            "once": Frequency.ONCE, "daily": Frequency.DAILY,
            "weekly": Frequency.WEEKLY, "monthly": Frequency.MONTHLY,
        }
        _type_map = {t.value: t for t in TaskType}

        if st.button("Add Task", use_container_width=True):
            # Validate optional time field
            validated_time = None
            if scheduled_time.strip():
                try:
                    h, m = scheduled_time.strip().split(":")
                    assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
                    validated_time = f"{int(h):02d}:{int(m):02d}"
                except Exception:
                    st.error("Scheduled time must be in HH:MM format (e.g. 08:30).")
                    st.stop()

            pet_obj = next(p for p in owner.pets if p.name == target_pet)
            pet_obj.add_task(Task(
                id=str(uuid.uuid4()),
                type=_type_map[task_type],
                priority=_priority_map[priority],
                frequency=_freq_map[frequency],
                time_for_task=timedelta(minutes=int(duration)),
                description=task_title,
                due_date=due_date,
                scheduled_time=validated_time,
            ))
            st.success(f"Task **{task_title}** added to **{target_pet}**.")

# ── RIGHT: Per-pet task list (sorted by priority) ───────────────────────────
with right:
    st.subheader("Current Tasks by Pet")

    if not owner.pets:
        st.info("No pets added yet.")
    else:
        for pet in owner.pets:
            with st.expander(f"**{pet.name}** ({pet.species})  —  "
                             f"{len(pet.task_list)} task(s)", expanded=True):
                if not pet.task_list:
                    st.caption("No tasks yet.")
                    continue
                sorted_tasks = pet.get_tasks_by_priority()
                st.table([
                    {
                        "Description":  t.description,
                        "Priority":     t.priority.name,
                        "Type":         t.type.value,
                        "Duration":     f"{int(t.time_for_task.total_seconds()//60)} min",
                        "Time":         t.scheduled_time or "—",
                        "Frequency":    t.frequency.value,
                        "Status":       t.status.name,
                    }
                    for t in sorted_tasks
                ])

# ---------------------------------------------------------------------------
# Generate Schedule
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Generate Daily Schedule")

if not owner.pets or not any(p.task_list for p in owner.pets):
    st.info("Add at least one pet and one task to generate a schedule.")
else:
    if st.button("Generate Schedule", use_container_width=False, type="primary"):
        scheduler = Scheduler(owner=owner)

        # ── Conflict warnings ──────────────────────────────────────────────
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.error(f"⚠️ **{len(conflicts)} scheduling conflict(s) detected — "
                     "please review before following this plan:**")
            for warning in conflicts:
                st.warning(warning)
        else:
            st.success("✅ No scheduling conflicts found.")

        # ── Ordered schedule ───────────────────────────────────────────────
        schedule = scheduler.schedule()
        if schedule:
            st.markdown("#### Today's Plan")
            st.caption("Timed tasks are shown first in chronological order, "
                       "followed by untimed tasks ordered by priority.")

            rows = []
            for i, t in enumerate(schedule, 1):
                rows.append({
                    "#":            i,
                    "Time":         t.scheduled_time or "—",
                    "Task":         t.description,
                    "Pet":          next(
                                        p.name for p in owner.pets
                                        if t in p.task_list
                                    ),
                    "Priority":     t.priority.name,
                    "Duration":     f"{int(t.time_for_task.total_seconds()//60)} min",
                    "Type":         t.type.value,
                })
            st.table(rows)
        else:
            st.info("No pending tasks to schedule.")
