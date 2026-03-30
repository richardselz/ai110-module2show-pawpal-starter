import uuid
import streamlit as st
from datetime import date, timedelta
from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    TaskType, Priority, TaskStatus, Frequency,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

if "owner" not in st.session_state:
    st.session_state.owner = Owner(id="o1", name="", email="")

owner: Owner = st.session_state.owner

st.subheader("Quick Demo Inputs")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name   = st.text_input("Pet name",   value="Mochi")
species    = st.selectbox("Species", ["dog", "cat", "other"])

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

_priority_map = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}

if st.button("Add task"):
    # Get or create the pet by name
    pet = next((p for p in owner.pets if p.name == pet_name), None)
    if pet is None:
        pet = Pet(id=pet_name, name=pet_name, species=species, breed="", birth_date=date.today())
        owner.add_pet(pet)
    pet.add_task(Task(
        id=f"{pet_name}-{len(pet.task_list)}",
        type=TaskType.OTHER,
        priority=_priority_map.get(priority, Priority.MEDIUM),
        frequency=Frequency.ONCE,
        time_for_task=timedelta(minutes=int(duration)),
        description=task_title,
        due_date=date.today(),
    ))

_active_pet = next((p for p in owner.pets if p.name == pet_name), None)
if _active_pet and _active_pet.task_list:
    st.write("Current tasks:")
    st.table([
        {"title": t.description, "duration_minutes": int(t.time_for_task.total_seconds() // 60), "priority": t.priority.name}
        for t in _active_pet.task_list
    ])
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    scheduler = Scheduler(owner=owner)
    all_tasks = scheduler.get_all_tasks()
    if all_tasks:
        st.table([
            {"task": t.description, "priority": t.priority.name, "status": t.status.name}
            for t in all_tasks
        ])
    else:
        st.info("No tasks scheduled yet. Add a pet and some tasks above.")
