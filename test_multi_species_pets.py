"""
Tests: PawPal+ core behaviours.

Covers:
  1. An owner can add multiple pets of different species
  2. Priority sorting works correctly (URGENT → HIGH → MEDIUM → LOW)
  3. Overlapping scheduled times are detected as conflicts
  4. All tasks show properly after being added for every pet type
  5. Remove the 2nd pet from a 5-pet list; the remaining 4 show correctly
"""

import pytest
from datetime import date, time, timedelta

from pawpal_system import (
    Owner, Pet, Task, Plan, TimeConstraint,
    TaskType, Priority, TaskStatus, Frequency, Scheduler,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_owner() -> Owner:
    return Owner(id="o1", name="Alex", email="alex@example.com")


def make_pet(species: str, name: str, pet_id: str | None = None) -> Pet:
    return Pet(
        id=pet_id or f"pet-{species.lower()}",
        name=name,
        species=species,
        breed="Mixed",
        birth_date=date(2020, 1, 1),
    )


def make_task(description: str, task_id: str | None = None) -> Task:
    return Task(
        id=task_id or f"task-{description[:8]}",
        type=TaskType.FEEDING,
        priority=Priority.MEDIUM,
        time_for_task=timedelta(minutes=15),
        description=description,
        frequency=Frequency.ONCE,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SPECIES_ROSTER = [
    ("dog",      "Buddy"),
    ("cat",      "Whiskers"),
    ("rabbit",   "Thumper"),
    ("hamster",  "Nibbles"),
    ("parrot",   "Polly"),
    ("fish",     "Nemo"),
    ("turtle",   "Shelly"),
    ("snake",    "Slinky"),
    ("guinea pig", "Peanut"),
    ("ferret",   "Bandit"),
]


@pytest.fixture()
def owner_with_two_pets():
    """Owner that has a dog and a cat."""
    owner = make_owner()
    owner.add_pet(make_pet("dog", "Rex", "p-dog"))
    owner.add_pet(make_pet("cat", "Luna", "p-cat"))
    return owner


@pytest.fixture()
def owner_with_full_zoo():
    """Owner that has one pet of each species in SPECIES_ROSTER."""
    owner = make_owner()
    for species, name in SPECIES_ROSTER:
        owner.add_pet(make_pet(species, name, f"pet-{species.replace(' ', '_')}"))
    return owner


# ---------------------------------------------------------------------------
# 1. Roster count
# ---------------------------------------------------------------------------

class TestRosterCount:
    def test_starts_empty(self):
        assert make_owner().pets == []

    def test_add_one_pet(self):
        owner = make_owner()
        owner.add_pet(make_pet("dog", "Rex"))
        assert len(owner.pets) == 1

    def test_add_two_different_species(self, owner_with_two_pets):
        assert len(owner_with_two_pets.pets) == 2

    def test_add_ten_different_species(self, owner_with_full_zoo):
        assert len(owner_with_full_zoo.pets) == len(SPECIES_ROSTER)


# ---------------------------------------------------------------------------
# 2. Identity — each pet is distinct
# ---------------------------------------------------------------------------

class TestPetIdentity:
    def test_all_ids_are_unique(self, owner_with_full_zoo):
        ids = [p.id for p in owner_with_full_zoo.pets]
        assert len(ids) == len(set(ids)), "Duplicate pet IDs found"

    def test_all_names_are_unique(self, owner_with_full_zoo):
        names = [p.name for p in owner_with_full_zoo.pets]
        assert len(names) == len(set(names)), "Duplicate pet names found"

    def test_all_species_are_unique(self, owner_with_full_zoo):
        species = [p.species for p in owner_with_full_zoo.pets]
        assert len(species) == len(set(species)), "Duplicate species found"


# ---------------------------------------------------------------------------
# 3. Species values are preserved exactly
# ---------------------------------------------------------------------------

class TestSpeciesPreservation:
    def test_dog_species_preserved(self, owner_with_two_pets):
        dog = next(p for p in owner_with_two_pets.pets if p.id == "p-dog")
        assert dog.species == "dog"

    def test_cat_species_preserved(self, owner_with_two_pets):
        cat = next(p for p in owner_with_two_pets.pets if p.id == "p-cat")
        assert cat.species == "cat"

    def test_all_species_in_zoo_preserved(self, owner_with_full_zoo):
        expected = {species for species, _ in SPECIES_ROSTER}
        actual   = {p.species for p in owner_with_full_zoo.pets}
        assert actual == expected

    def test_species_with_space_preserved(self):
        """'guinea pig' contains a space — must not be mangled."""
        owner = make_owner()
        gp = make_pet("guinea pig", "Peanut", "p-gp")
        owner.add_pet(gp)
        found = owner.pets[0]
        assert found.species == "guinea pig"


# ---------------------------------------------------------------------------
# 4. Scheduler awareness: get_tasks_by_pet
# ---------------------------------------------------------------------------

class TestSchedulerTasksByPet:
    def test_all_species_appear_as_keys(self, owner_with_full_zoo):
        scheduler = Scheduler(owner=owner_with_full_zoo)
        by_pet = scheduler.get_tasks_by_pet()
        pet_names = {p.name for p in owner_with_full_zoo.pets}
        assert set(by_pet.keys()) == pet_names

    def test_two_pets_both_appear(self, owner_with_two_pets):
        scheduler = Scheduler(owner=owner_with_two_pets)
        by_pet = scheduler.get_tasks_by_pet()
        assert "Rex" in by_pet
        assert "Luna" in by_pet


# ---------------------------------------------------------------------------
# 5. Task isolation — tasks don't leak between pets
# ---------------------------------------------------------------------------

class TestTaskIsolation:
    def test_dog_task_not_on_cat(self, owner_with_two_pets):
        dog = next(p for p in owner_with_two_pets.pets if p.id == "p-dog")
        cat = next(p for p in owner_with_two_pets.pets if p.id == "p-cat")

        dog_task = make_task("Feed Rex kibble", "t-dog")
        dog.add_task(dog_task)

        assert dog_task in dog.task_list
        assert dog_task not in cat.task_list

    def test_each_pet_has_only_its_own_tasks(self, owner_with_full_zoo):
        # Give every pet exactly one uniquely-described task
        for pet in owner_with_full_zoo.pets:
            pet.add_task(make_task(f"Feed {pet.name}", f"t-{pet.id}"))

        for pet in owner_with_full_zoo.pets:
            assert len(pet.task_list) == 1
            assert pet.task_list[0].description == f"Feed {pet.name}"

    def test_scheduler_get_all_tasks_aggregates_all_species(self, owner_with_full_zoo):
        for pet in owner_with_full_zoo.pets:
            pet.add_task(make_task(f"Walk {pet.name}", f"tw-{pet.id}"))

        scheduler = Scheduler(owner=owner_with_full_zoo)
        all_tasks = scheduler.get_all_tasks()
        assert len(all_tasks) == len(SPECIES_ROSTER)


# ---------------------------------------------------------------------------
# 6. Removal — deleting one pet leaves the rest intact
# ---------------------------------------------------------------------------

class TestPetRemoval:
    def test_remove_dog_leaves_cat(self, owner_with_two_pets):
        owner_with_two_pets.remove_pet("p-dog")
        remaining_species = [p.species for p in owner_with_two_pets.pets]
        assert "cat" in remaining_species
        assert "dog" not in remaining_species

    def test_remove_one_from_zoo_leaves_nine(self, owner_with_full_zoo):
        owner_with_full_zoo.remove_pet("pet-dog")
        assert len(owner_with_full_zoo.pets) == len(SPECIES_ROSTER) - 1

    def test_removed_pets_tasks_no_longer_in_scheduler(self, owner_with_two_pets):
        dog = next(p for p in owner_with_two_pets.pets if p.id == "p-dog")
        dog_task = make_task("Dog walk", "t-walk")
        dog.add_task(dog_task)

        owner_with_two_pets.remove_pet("p-dog")

        scheduler = Scheduler(owner=owner_with_two_pets)
        assert dog_task not in scheduler.get_all_tasks()


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_same_species_twice_both_kept(self):
        """Two dogs are legal; only names/ids differ."""
        owner = make_owner()
        owner.add_pet(make_pet("dog", "Rex", "dog-1"))
        owner.add_pet(make_pet("dog", "Max", "dog-2"))
        assert len(owner.pets) == 2
        species_list = [p.species for p in owner.pets]
        assert species_list.count("dog") == 2

    def test_add_pet_does_not_mutate_other_pets(self):
        owner = make_owner()
        dog = make_pet("dog", "Rex", "p-dog")
        owner.add_pet(dog)
        original_id = dog.id

        owner.add_pet(make_pet("cat", "Luna", "p-cat"))
        assert dog.id == original_id  # dog object unchanged

    def test_owner_all_tasks_empty_when_no_pets(self):
        owner = make_owner()
        assert owner.get_all_tasks() == []

    def test_owner_all_tasks_empty_when_pets_have_no_tasks(self, owner_with_two_pets):
        assert owner_with_two_pets.get_all_tasks() == []


# ===========================================================================
# 2. Priority sorting
# ===========================================================================

class TestPrioritySorting:
    """
    Priority enum values: LOW=1  MEDIUM=2  HIGH=3  URGENT=4
    Both Pet.get_tasks_by_priority() and Scheduler.get_tasks_by_priority()
    must return tasks in descending order (URGENT first).
    """

    def _make_task_with_priority(self, priority: Priority, label: str) -> Task:
        return Task(
            id=f"t-{label}",
            type=TaskType.FEEDING,
            priority=priority,
            time_for_task=timedelta(minutes=10),
            description=label,
        )

    # --- Pet-level ---

    def test_pet_sorts_urgent_first(self):
        pet = make_pet("dog", "Rex")
        pet.add_task(self._make_task_with_priority(Priority.LOW,    "low"))
        pet.add_task(self._make_task_with_priority(Priority.URGENT, "urgent"))
        pet.add_task(self._make_task_with_priority(Priority.MEDIUM, "medium"))
        pet.add_task(self._make_task_with_priority(Priority.HIGH,   "high"))

        sorted_tasks = pet.get_tasks_by_priority()
        priorities = [t.priority for t in sorted_tasks]
        assert priorities == [Priority.URGENT, Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def test_pet_priority_all_same_returns_all(self):
        pet = make_pet("cat", "Luna")
        for i in range(3):
            pet.add_task(self._make_task_with_priority(Priority.HIGH, f"task-{i}"))
        sorted_tasks = pet.get_tasks_by_priority()
        assert len(sorted_tasks) == 3
        assert all(t.priority == Priority.HIGH for t in sorted_tasks)

    def test_pet_priority_single_task(self):
        pet = make_pet("rabbit", "Thumper")
        pet.add_task(self._make_task_with_priority(Priority.LOW, "only-task"))
        assert pet.get_tasks_by_priority()[0].priority == Priority.LOW

    def test_pet_priority_does_not_mutate_original_list(self):
        pet = make_pet("parrot", "Polly")
        pet.add_task(self._make_task_with_priority(Priority.LOW,    "low"))
        pet.add_task(self._make_task_with_priority(Priority.URGENT, "urgent"))
        original_order = [t.description for t in pet.task_list]
        pet.get_tasks_by_priority()
        assert [t.description for t in pet.task_list] == original_order

    # --- Scheduler-level (across multiple pets / species) ---

    def test_scheduler_sorts_pending_urgent_first(self):
        owner = make_owner()
        dog = make_pet("dog", "Rex", "p1")
        cat = make_pet("cat", "Luna", "p2")
        dog.add_task(self._make_task_with_priority(Priority.LOW,    "dog-low"))
        cat.add_task(self._make_task_with_priority(Priority.URGENT, "cat-urgent"))
        owner.add_pet(dog)
        owner.add_pet(cat)

        scheduler = Scheduler(owner=owner)
        sorted_tasks = scheduler.get_tasks_by_priority()
        assert sorted_tasks[0].priority == Priority.URGENT
        assert sorted_tasks[-1].priority == Priority.LOW

    def test_scheduler_priority_descending_across_all_pets(self):
        owner = make_owner()
        priorities_to_add = [Priority.MEDIUM, Priority.URGENT, Priority.LOW, Priority.HIGH]
        for i, priority in enumerate(priorities_to_add):
            pet = make_pet(f"species-{i}", f"Pet{i}", f"pid-{i}")
            pet.add_task(self._make_task_with_priority(priority, f"task-{i}"))
            owner.add_pet(pet)

        scheduler = Scheduler(owner=owner)
        sorted_tasks = scheduler.get_tasks_by_priority()
        values = [t.priority.value for t in sorted_tasks]
        assert values == sorted(values, reverse=True)

    def test_scheduler_excludes_completed_from_priority_list(self):
        owner = make_owner()
        dog = make_pet("dog", "Rex", "p-dog")
        urgent = self._make_task_with_priority(Priority.URGENT, "urgent")
        done   = self._make_task_with_priority(Priority.HIGH,   "done")
        done.complete()
        dog.add_task(urgent)
        dog.add_task(done)
        owner.add_pet(dog)

        scheduler = Scheduler(owner=owner)
        result = scheduler.get_tasks_by_priority()
        assert all(t.status == TaskStatus.PENDING for t in result)
        assert urgent in result
        assert done not in result


# ===========================================================================
# 3. Conflict detection (overlapping scheduled times)
# ===========================================================================

class TestConflictDetection:
    """
    Two tasks conflict when their time windows overlap:
      task_a: [start_a, start_a + duration_a)
      task_b: [start_b, start_b + duration_b)
    detect_conflicts() returns human-readable warning strings.
    """

    def _make_timed_task(
        self,
        description: str,
        scheduled_time: str,
        duration_minutes: int,
        task_id: str | None = None,
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        t = Task(
            id=task_id or f"t-{description[:6]}",
            type=TaskType.FEEDING,
            priority=Priority.MEDIUM,
            time_for_task=timedelta(minutes=duration_minutes),
            description=description,
            scheduled_time=scheduled_time,
            status=status,
        )
        return t

    def _scheduler_with_tasks(self, tasks: list[Task]) -> Scheduler:
        owner = make_owner()
        pet   = make_pet("dog", "Rex", "p1")
        for t in tasks:
            pet.add_task(t)
        owner.add_pet(pet)
        return Scheduler(owner=owner)

    # --- No conflict cases ---

    def test_no_conflict_sequential_tasks(self):
        """09:00–09:30, then 09:30–10:00 — end of A == start of B, no overlap."""
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Morning feed",   "09:00", 30, "t1"),
            self._make_timed_task("Morning walk",   "09:30", 30, "t2"),
        ])
        assert scheduler.detect_conflicts() == []

    def test_no_conflict_gap_between_tasks(self):
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Task A", "08:00", 20, "t1"),
            self._make_timed_task("Task B", "09:00", 20, "t2"),
        ])
        assert scheduler.detect_conflicts() == []

    def test_no_conflict_single_task(self):
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Solo task", "10:00", 30, "t1"),
        ])
        assert scheduler.detect_conflicts() == []

    def test_no_conflict_no_scheduled_time(self):
        """Tasks without scheduled_time are ignored by conflict detection."""
        owner = make_owner()
        pet   = make_pet("cat", "Luna", "p1")
        pet.add_task(make_task("Untimed task A", "t1"))
        pet.add_task(make_task("Untimed task B", "t2"))
        owner.add_pet(pet)
        assert Scheduler(owner=owner).detect_conflicts() == []

    # --- Conflict cases ---

    def test_full_overlap_detected(self):
        """Task B starts during Task A — clear conflict."""
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Groom Rex",  "10:00", 60, "t1"),
            self._make_timed_task("Vet visit",  "10:30", 30, "t2"),
        ])
        warnings = scheduler.detect_conflicts()
        assert len(warnings) == 1
        assert "Groom Rex" in warnings[0]
        assert "Vet visit" in warnings[0]

    def test_partial_overlap_detected(self):
        """Task A: 08:00–08:45, Task B: 08:30–09:00 — 15-min overlap."""
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Feed breakfast", "08:00", 45, "t1"),
            self._make_timed_task("Morning meds",   "08:30", 30, "t2"),
        ])
        warnings = scheduler.detect_conflicts()
        assert len(warnings) == 1

    def test_three_tasks_two_conflicts(self):
        """A overlaps B and A overlaps C → 2 warnings."""
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Task A", "09:00", 90, "t1"),  # 09:00–10:30
            self._make_timed_task("Task B", "09:15", 30, "t2"),  # 09:15–09:45
            self._make_timed_task("Task C", "10:00", 30, "t3"),  # 10:00–10:30
        ])
        warnings = scheduler.detect_conflicts()
        assert len(warnings) == 2

    def test_conflict_across_different_pets(self):
        """Conflicts between tasks belonging to two different pets."""
        owner = make_owner()

        dog = make_pet("dog", "Rex",  "p-dog")
        cat = make_pet("cat", "Luna", "p-cat")
        dog.add_task(self._make_timed_task("Walk Rex",    "14:00", 60, "t-dog"))
        cat.add_task(self._make_timed_task("Groom Luna",  "14:30", 30, "t-cat"))
        owner.add_pet(dog)
        owner.add_pet(cat)

        warnings = Scheduler(owner=owner).detect_conflicts()
        assert len(warnings) == 1
        assert "Walk Rex"   in warnings[0]
        assert "Groom Luna" in warnings[0]

    def test_completed_tasks_excluded_from_conflict_check(self):
        """A completed task cannot conflict — it is already done."""
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Task A", "10:00", 60, "t1", status=TaskStatus.COMPLETED),
            self._make_timed_task("Task B", "10:30", 30, "t2", status=TaskStatus.PENDING),
        ])
        assert scheduler.detect_conflicts() == []

    def test_warning_string_contains_time_range(self):
        """Warning message must include both tasks' start times."""
        scheduler = self._scheduler_with_tasks([
            self._make_timed_task("Feed cat",  "07:00", 30, "t1"),
            self._make_timed_task("Feed dog",  "07:15", 30, "t2"),
        ])
        warning = scheduler.detect_conflicts()[0]
        assert "07:00" in warning
        assert "07:15" in warning


# ===========================================================================
# 4. All tasks show after being added for every pet type
# ===========================================================================

class TestAllTasksVisible:
    """
    After tasks are added to pets of every species, every task must be
    retrievable — via the pet directly and via the Scheduler.
    """

    # Maps species → task descriptions for that species
    SPECIES_TASKS = {
        "dog":       ["Feed kibble",   "Morning walk",  "Brush coat"],
        "cat":       ["Fill bowl",     "Clean litter",  "Playtime"],
        "rabbit":    ["Hay refill",    "Pellets",       "Cage clean"],
        "hamster":   ["Water bottle",  "Wheel check",   "Bedding"],
        "parrot":    ["Seed mix",      "Mist feathers", "Socialise"],
        "fish":      ["Feed flakes",   "Check filter",  "Water test"],
        "turtle":    ["Lettuce feed",  "UV lamp check", "Tank clean"],
        "snake":     ["Thaw mouse",    "Humidity check","Shedding check"],
        "guinea pig":["Veg chop",      "Hay refill",    "Cuddle time"],
        "ferret":    ["Raw feed",      "Tunnel clean",  "Playtime"],
    }

    @pytest.fixture()
    def loaded_owner(self):
        owner = make_owner()
        for i, (species, tasks) in enumerate(self.SPECIES_TASKS.items()):
            pet = make_pet(species, species.capitalize(), f"pid-{i}")
            for j, desc in enumerate(tasks):
                pet.add_task(make_task(desc, f"t-{i}-{j}"))
            owner.add_pet(pet)
        return owner

    def test_total_task_count_matches(self, loaded_owner):
        expected = sum(len(v) for v in self.SPECIES_TASKS.values())
        scheduler = Scheduler(owner=loaded_owner)
        assert len(scheduler.get_all_tasks()) == expected

    def test_each_pet_has_correct_task_count(self, loaded_owner):
        for pet in loaded_owner.pets:
            expected = len(self.SPECIES_TASKS[pet.species])
            assert len(pet.task_list) == expected, (
                f"{pet.species} should have {expected} tasks, got {len(pet.task_list)}"
            )

    def test_each_pet_task_descriptions_match(self, loaded_owner):
        for pet in loaded_owner.pets:
            actual_descs   = {t.description for t in pet.task_list}
            expected_descs = set(self.SPECIES_TASKS[pet.species])
            assert actual_descs == expected_descs, (
                f"Task mismatch for {pet.species}: {actual_descs} != {expected_descs}"
            )

    def test_scheduler_get_tasks_by_pet_has_all_tasks(self, loaded_owner):
        scheduler = Scheduler(owner=loaded_owner)
        by_pet = scheduler.get_tasks_by_pet()
        for pet in loaded_owner.pets:
            expected_count = len(self.SPECIES_TASKS[pet.species])
            assert len(by_pet[pet.name]) == expected_count

    def test_all_tasks_are_pending_by_default(self, loaded_owner):
        scheduler = Scheduler(owner=loaded_owner)
        assert all(t.status == TaskStatus.PENDING for t in scheduler.get_all_tasks())

    def test_filter_by_pet_name_returns_only_that_pets_tasks(self, loaded_owner):
        scheduler = Scheduler(owner=loaded_owner)
        dog_tasks = scheduler.filter_tasks(pet_name="dog")
        expected  = set(self.SPECIES_TASKS["dog"])
        assert {t.description for t in dog_tasks} == expected

    def test_no_tasks_lost_after_one_pet_completes_a_task(self, loaded_owner):
        """Completing a task on one pet must not affect other pets' task lists."""
        scheduler = Scheduler(owner=loaded_owner)
        dog = next(p for p in loaded_owner.pets if p.species == "dog")
        scheduler.complete_task(dog.task_list[0], dog)

        total_expected = sum(len(v) for v in self.SPECIES_TASKS.values())
        # One-time tasks: completing adds no new task, so total stays the same
        assert len(scheduler.get_all_tasks()) == total_expected


# ===========================================================================
# 5. Add 5 pets, remove the 2nd, remaining 4 display correctly
# ===========================================================================

class TestRemoveSecondPet:
    """
    Roster: [dog, cat, rabbit, hamster, parrot]  (indices 0–4)
    Remove index 1 (cat). Remaining: dog, rabbit, hamster, parrot.
    Verify order, ids, task isolation, and Scheduler consistency.
    """

    FIVE_PETS = [
        ("dog",     "Buddy",   "p0"),
        ("cat",     "Whiskers","p1"),   # ← will be removed
        ("rabbit",  "Thumper", "p2"),
        ("hamster", "Nibbles", "p3"),
        ("parrot",  "Polly",   "p4"),
    ]
    EXPECTED_AFTER_REMOVAL = [("dog","Buddy","p0"),("rabbit","Thumper","p2"),
                               ("hamster","Nibbles","p3"),("parrot","Polly","p4")]

    @pytest.fixture()
    def owner_five_pets(self):
        owner = make_owner()
        for species, name, pid in self.FIVE_PETS:
            pet = make_pet(species, name, pid)
            pet.add_task(make_task(f"Task for {name}", f"t-{pid}"))
            owner.add_pet(pet)
        return owner

    @pytest.fixture()
    def owner_after_removal(self, owner_five_pets):
        owner_five_pets.remove_pet("p1")   # remove cat "Whiskers"
        return owner_five_pets

    # --- Count ---

    def test_five_pets_before_removal(self, owner_five_pets):
        assert len(owner_five_pets.pets) == 5

    def test_four_pets_after_removal(self, owner_after_removal):
        assert len(owner_after_removal.pets) == 4

    # --- Removed pet is truly gone ---

    def test_removed_pet_id_absent(self, owner_after_removal):
        ids = [p.id for p in owner_after_removal.pets]
        assert "p1" not in ids

    def test_removed_pet_name_absent(self, owner_after_removal):
        names = [p.name for p in owner_after_removal.pets]
        assert "Whiskers" not in names

    def test_removed_pet_species_absent(self, owner_after_removal):
        species = [p.species for p in owner_after_removal.pets]
        assert "cat" not in species

    # --- Remaining pets are correct ---

    def test_remaining_pet_ids_correct(self, owner_after_removal):
        ids = [p.id for p in owner_after_removal.pets]
        assert ids == ["p0", "p2", "p3", "p4"]

    def test_remaining_pet_names_correct(self, owner_after_removal):
        names = [p.name for p in owner_after_removal.pets]
        assert names == ["Buddy", "Thumper", "Nibbles", "Polly"]

    def test_remaining_pet_species_correct(self, owner_after_removal):
        species = [p.species for p in owner_after_removal.pets]
        assert species == ["dog", "rabbit", "hamster", "parrot"]

    # --- Task integrity ---

    def test_removed_pets_task_gone_from_scheduler(self, owner_after_removal):
        scheduler = Scheduler(owner=owner_after_removal)
        descriptions = [t.description for t in scheduler.get_all_tasks()]
        assert "Task for Whiskers" not in descriptions

    def test_remaining_pets_tasks_all_present(self, owner_after_removal):
        scheduler = Scheduler(owner=owner_after_removal)
        descriptions = {t.description for t in scheduler.get_all_tasks()}
        for _, name, _ in self.EXPECTED_AFTER_REMOVAL:
            assert f"Task for {name}" in descriptions

    def test_scheduler_task_count_is_four(self, owner_after_removal):
        scheduler = Scheduler(owner=owner_after_removal)
        assert len(scheduler.get_all_tasks()) == 4

    def test_scheduler_get_tasks_by_pet_has_no_removed_pet(self, owner_after_removal):
        by_pet = Scheduler(owner=owner_after_removal).get_tasks_by_pet()
        assert "Whiskers" not in by_pet

    def test_scheduler_get_tasks_by_pet_has_all_remaining(self, owner_after_removal):
        by_pet = Scheduler(owner=owner_after_removal).get_tasks_by_pet()
        for _, name, _ in self.EXPECTED_AFTER_REMOVAL:
            assert name in by_pet

    # --- Idempotence: removing non-existent id is a no-op ---

    def test_remove_already_removed_pet_is_safe(self, owner_after_removal):
        owner_after_removal.remove_pet("p1")   # second removal
        assert len(owner_after_removal.pets) == 4


# ===========================================================================
# 6. Sorting Correctness — sort_by_time() returns tasks in chronological order
# ===========================================================================

class TestSortByTime:
    """
    Scheduler.sort_by_time() must return tasks ordered by scheduled_time
    ascending (HH:MM string comparison). Tasks without a scheduled_time
    are placed after all timed tasks.
    """

    def _timed(self, desc: str, scheduled_time: str, task_id: str) -> Task:
        return Task(
            id=task_id,
            type=TaskType.FEEDING,
            priority=Priority.MEDIUM,
            time_for_task=timedelta(minutes=15),
            description=desc,
            scheduled_time=scheduled_time,
        )

    def _untimed(self, desc: str, task_id: str) -> Task:
        return Task(
            id=task_id,
            type=TaskType.FEEDING,
            priority=Priority.MEDIUM,
            time_for_task=timedelta(minutes=15),
            description=desc,
        )

    @pytest.fixture()
    def scheduler(self):
        owner = make_owner()
        pet = make_pet("dog", "Rex", "p1")
        owner.add_pet(pet)
        return Scheduler(owner=owner), pet

    def test_two_tasks_returned_earliest_first(self, scheduler):
        sched, pet = scheduler
        pet.add_task(self._timed("Late task",  "14:00", "t1"))
        pet.add_task(self._timed("Early task", "08:00", "t2"))
        result = sched.sort_by_time()
        assert result[0].scheduled_time == "08:00"
        assert result[1].scheduled_time == "14:00"

    def test_four_tasks_fully_sorted(self, scheduler):
        sched, pet = scheduler
        times = ["12:00", "07:30", "09:15", "06:00"]
        for i, t in enumerate(times):
            pet.add_task(self._timed(f"Task {i}", t, f"t{i}"))
        result = sched.sort_by_time()
        actual_times = [t.scheduled_time for t in result]
        assert actual_times == sorted(actual_times)

    def test_untimed_tasks_placed_after_timed(self, scheduler):
        sched, pet = scheduler
        pet.add_task(self._untimed("No time A", "u1"))
        pet.add_task(self._timed("08:00 task", "08:00", "t1"))
        pet.add_task(self._untimed("No time B", "u2"))
        result = sched.sort_by_time()
        timed_indices   = [i for i, t in enumerate(result) if t.scheduled_time]
        untimed_indices = [i for i, t in enumerate(result) if not t.scheduled_time]
        assert max(timed_indices) < min(untimed_indices)

    def test_all_untimed_tasks_order_preserved(self, scheduler):
        """When no task has a time, the list comes back unchanged in relative order."""
        sched, pet = scheduler
        pet.add_task(self._untimed("First",  "u1"))
        pet.add_task(self._untimed("Second", "u2"))
        pet.add_task(self._untimed("Third",  "u3"))
        result = sched.sort_by_time()
        assert [t.description for t in result] == ["First", "Second", "Third"]

    def test_single_task_returns_single_item(self, scheduler):
        sched, pet = scheduler
        pet.add_task(self._timed("Solo", "10:00", "t1"))
        assert len(sched.sort_by_time()) == 1

    def test_tasks_across_multiple_pets_sorted_together(self):
        """sort_by_time across two pets must interleave correctly."""
        owner = make_owner()
        dog = make_pet("dog", "Rex",  "p1")
        cat = make_pet("cat", "Luna", "p2")
        dog.add_task(Task("d1", TaskType.FEEDING, Priority.LOW,
                          timedelta(minutes=10), "Dog afternoon",
                          scheduled_time="15:00"))
        cat.add_task(Task("c1", TaskType.FEEDING, Priority.LOW,
                          timedelta(minutes=10), "Cat morning",
                          scheduled_time="07:00"))
        owner.add_pet(dog)
        owner.add_pet(cat)
        result = Scheduler(owner=owner).sort_by_time()
        assert result[0].description == "Cat morning"
        assert result[1].description == "Dog afternoon"

    def test_schedule_method_timed_before_untimed(self):
        """Scheduler.schedule() puts timed pending tasks before untimed ones."""
        owner = make_owner()
        pet = make_pet("rabbit", "Thumper", "p1")
        pet.add_task(Task("u1", TaskType.FEEDING, Priority.URGENT,
                          timedelta(minutes=10), "Urgent untimed"))
        pet.add_task(Task("t1", TaskType.FEEDING, Priority.LOW,
                          timedelta(minutes=10), "Low timed",
                          scheduled_time="09:00"))
        owner.add_pet(pet)
        result = Scheduler(owner=owner).schedule()
        assert result[0].scheduled_time == "09:00"   # timed goes first
        assert result[1].scheduled_time is None       # untimed follows


# ===========================================================================
# 7. Recurrence Logic — completing a DAILY task spawns the next occurrence
# ===========================================================================

class TestRecurrenceLogic:
    """
    Scheduler.complete_task(task, pet):
      - Marks the task COMPLETED
      - For DAILY tasks: creates a new PENDING task due the following day
      - For ONCE tasks:  returns None, no new task is added
      - The new task is a fresh copy (new id, same type/priority/description)
    """

    def _daily_task(self, desc: str = "Daily feed", task_id: str = "t1") -> Task:
        return Task(
            id=task_id,
            type=TaskType.FEEDING,
            priority=Priority.HIGH,
            time_for_task=timedelta(minutes=20),
            description=desc,
            frequency=Frequency.DAILY,
            due_date=date(2026, 3, 29),
        )

    def _once_task(self, desc: str = "One-off vet", task_id: str = "t2") -> Task:
        return Task(
            id=task_id,
            type=TaskType.VET_VISIT,
            priority=Priority.URGENT,
            time_for_task=timedelta(minutes=60),
            description=desc,
            frequency=Frequency.ONCE,
            due_date=date(2026, 3, 29),
        )

    @pytest.fixture()
    def pet_and_scheduler(self):
        owner = make_owner()
        pet = make_pet("dog", "Rex", "p1")
        owner.add_pet(pet)
        return pet, Scheduler(owner=owner)

    # --- Original task is marked complete ---

    def test_original_task_status_becomes_completed(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        sched.complete_task(task, pet)
        assert task.status == TaskStatus.COMPLETED

    # --- New task is created ---

    def test_daily_complete_returns_new_task(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task is not None

    def test_daily_complete_adds_task_to_pet(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        sched.complete_task(task, pet)
        assert len(pet.task_list) == 2

    # --- New task is due the following day ---

    def test_new_task_due_date_is_next_day(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.due_date == date(2026, 3, 30)  # one day after 2026-03-29

    # --- New task is a fresh, independent copy ---

    def test_new_task_has_different_id(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.id != task.id

    def test_new_task_is_pending(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.status == TaskStatus.PENDING

    def test_new_task_preserves_description(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task("Feed Rex kibble")
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.description == "Feed Rex kibble"

    def test_new_task_preserves_priority(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.priority == Priority.HIGH

    def test_new_task_preserves_frequency(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.frequency == Frequency.DAILY

    # --- ONCE task: no recurrence ---

    def test_once_task_returns_none(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._once_task()
        pet.add_task(task)
        result = sched.complete_task(task, pet)
        assert result is None

    def test_once_task_does_not_add_new_task(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._once_task()
        pet.add_task(task)
        sched.complete_task(task, pet)
        assert len(pet.task_list) == 1

    # --- Weekly and Monthly recurrence ---

    def test_weekly_task_due_seven_days_later(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = Task("tw", TaskType.GROOMING, Priority.MEDIUM,
                    timedelta(minutes=30), "Weekly groom",
                    frequency=Frequency.WEEKLY, due_date=date(2026, 3, 29))
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.due_date == date(2026, 4, 5)

    def test_monthly_task_due_thirty_days_later(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = Task("tm", TaskType.VET_VISIT, Priority.HIGH,
                    timedelta(minutes=60), "Monthly vet",
                    frequency=Frequency.MONTHLY, due_date=date(2026, 3, 29))
        pet.add_task(task)
        new_task = sched.complete_task(task, pet)
        assert new_task.due_date == date(2026, 4, 28)

    # --- Chain: completing the new task spawns yet another ---

    def test_completing_new_task_chains_again(self, pet_and_scheduler):
        pet, sched = pet_and_scheduler
        task = self._daily_task()
        pet.add_task(task)
        day2_task = sched.complete_task(task, pet)
        day3_task = sched.complete_task(day2_task, pet)
        assert day3_task.due_date == date(2026, 3, 31)
        assert len(pet.task_list) == 3


# ===========================================================================
# 8. Conflict Detection — exact duplicate (same) start time
# ===========================================================================

class TestDuplicateTimeConflict:
    """
    Two tasks scheduled at the identical start time are always overlapping
    (assuming non-zero duration). detect_conflicts() must flag this.
    """

    def _timed(self, desc: str, scheduled_time: str,
               duration_minutes: int, task_id: str) -> Task:
        return Task(
            id=task_id,
            type=TaskType.FEEDING,
            priority=Priority.MEDIUM,
            time_for_task=timedelta(minutes=duration_minutes),
            description=desc,
            scheduled_time=scheduled_time,
        )

    def _scheduler_for(self, *tasks: Task) -> Scheduler:
        owner = make_owner()
        pet = make_pet("dog", "Rex", "p1")
        for t in tasks:
            pet.add_task(t)
        owner.add_pet(pet)
        return Scheduler(owner=owner)

    def test_identical_start_time_flagged(self):
        sched = self._scheduler_for(
            self._timed("Morning feed",  "08:00", 30, "t1"),
            self._timed("Morning meds",  "08:00", 15, "t2"),
        )
        warnings = sched.detect_conflicts()
        assert len(warnings) == 1

    def test_identical_start_time_warning_names_both_tasks(self):
        sched = self._scheduler_for(
            self._timed("Morning feed", "08:00", 30, "t1"),
            self._timed("Morning meds", "08:00", 15, "t2"),
        )
        warning = sched.detect_conflicts()[0]
        assert "Morning feed" in warning
        assert "Morning meds" in warning

    def test_three_tasks_same_time_all_pairs_flagged(self):
        """3 tasks at the same time → 3 conflicting pairs."""
        sched = self._scheduler_for(
            self._timed("Task A", "10:00", 20, "t1"),
            self._timed("Task B", "10:00", 20, "t2"),
            self._timed("Task C", "10:00", 20, "t3"),
        )
        assert len(sched.detect_conflicts()) == 3

    def test_duplicate_time_across_two_pets(self):
        """Same start time on different pets still triggers a conflict."""
        owner = make_owner()
        dog = make_pet("dog",  "Rex",  "p1")
        cat = make_pet("cat",  "Luna", "p2")
        dog.add_task(self._timed("Walk Rex",   "09:00", 30, "t-dog"))
        cat.add_task(self._timed("Feed Luna",  "09:00", 15, "t-cat"))
        owner.add_pet(dog)
        owner.add_pet(cat)
        warnings = Scheduler(owner=owner).detect_conflicts()
        assert len(warnings) == 1

    def test_duplicate_time_one_minute_duration_still_conflicts(self):
        """Even a 1-minute task at the same time as another must conflict."""
        sched = self._scheduler_for(
            self._timed("Quick pill",   "07:00",  1, "t1"),
            self._timed("Morning feed", "07:00", 30, "t2"),
        )
        assert len(sched.detect_conflicts()) == 1

    def test_no_false_positive_one_minute_apart(self):
        """07:00 + 1 min ends at 07:01; a task starting at 07:01 must NOT conflict."""
        sched = self._scheduler_for(
            self._timed("Quick pill",  "07:00",  1, "t1"),
            self._timed("Next task",   "07:01", 30, "t2"),
        )
        assert sched.detect_conflicts() == []


# ===========================================================================
# 9. TimeConstraint.is_available()
# ===========================================================================

class TestTimeConstraintIsAvailable:
    """TimeConstraint.is_available(check_time) returns True iff
    start_time <= check_time <= end_time."""

    @pytest.fixture()
    def window(self):
        return TimeConstraint(
            day_of_week="Monday",
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

    def test_time_inside_window_is_available(self, window):
        assert window.is_available(time(12, 0)) is True

    def test_time_at_start_boundary_is_available(self, window):
        assert window.is_available(time(9, 0)) is True

    def test_time_at_end_boundary_is_available(self, window):
        assert window.is_available(time(17, 0)) is True

    def test_time_before_window_is_not_available(self, window):
        assert window.is_available(time(8, 59)) is False

    def test_time_after_window_is_not_available(self, window):
        assert window.is_available(time(17, 1)) is False

    def test_midnight_edge_case(self):
        window = TimeConstraint("Sunday", time(0, 0), time(23, 59))
        assert window.is_available(time(0, 0)) is True
        assert window.is_available(time(23, 59)) is True


# ===========================================================================
# 10. Task.start() and Task.skip()
# ===========================================================================

class TestTaskStatusTransitions:

    def test_start_sets_in_progress(self):
        task = make_task("Morning walk", "t1")
        assert task.status == TaskStatus.PENDING
        task.start()
        assert task.status == TaskStatus.IN_PROGRESS

    def test_skip_sets_skipped(self):
        task = make_task("Vet visit", "t1")
        task.skip()
        assert task.status == TaskStatus.SKIPPED

    def test_start_then_complete(self):
        task = make_task("Grooming", "t1")
        task.start()
        task.complete()
        assert task.status == TaskStatus.COMPLETED

    def test_skip_is_independent_of_start(self):
        task = make_task("Exercise", "t1")
        task.skip()
        assert task.status == TaskStatus.SKIPPED

    def test_in_progress_task_excluded_from_pending(self):
        pet = make_pet("dog", "Rex", "p1")
        t1 = make_task("Task A", "t1")
        t2 = make_task("Task B", "t2")
        t1.start()
        pet.add_task(t1)
        pet.add_task(t2)
        pending = pet.get_pending_tasks()
        assert t2 in pending
        assert t1 not in pending

    def test_skipped_task_excluded_from_pending(self):
        pet = make_pet("cat", "Luna", "p1")
        t1 = make_task("Task A", "t1")
        t2 = make_task("Task B", "t2")
        t1.skip()
        pet.add_task(t1)
        pet.add_task(t2)
        assert t1 not in pet.get_pending_tasks()
        assert t2 in pet.get_pending_tasks()


# ===========================================================================
# 11. Pet.remove_task() and Pet.get_pending_tasks()
# ===========================================================================

class TestPetTaskManagement:

    def test_remove_task_by_id(self):
        pet = make_pet("rabbit", "Thumper", "p1")
        t1 = make_task("Feed hay", "t1")
        t2 = make_task("Clean cage", "t2")
        pet.add_task(t1)
        pet.add_task(t2)
        pet.remove_task("t1")
        assert t1 not in pet.task_list
        assert t2 in pet.task_list

    def test_remove_task_reduces_count(self):
        pet = make_pet("hamster", "Nibbles", "p1")
        pet.add_task(make_task("Water", "t1"))
        pet.add_task(make_task("Feed", "t2"))
        pet.remove_task("t1")
        assert len(pet.task_list) == 1

    def test_remove_nonexistent_task_is_safe(self):
        pet = make_pet("parrot", "Polly", "p1")
        pet.add_task(make_task("Socialise", "t1"))
        pet.remove_task("does-not-exist")
        assert len(pet.task_list) == 1

    def test_remove_all_tasks_leaves_empty_list(self):
        pet = make_pet("fish", "Nemo", "p1")
        pet.add_task(make_task("Feed flakes", "t1"))
        pet.remove_task("t1")
        assert pet.task_list == []

    def test_get_pending_tasks_returns_only_pending(self):
        pet = make_pet("dog", "Rex", "p1")
        t_pending   = make_task("Pending task",   "t1")
        t_completed = make_task("Completed task", "t2")
        t_skipped   = make_task("Skipped task",   "t3")
        t_completed.complete()
        t_skipped.skip()
        pet.add_task(t_pending)
        pet.add_task(t_completed)
        pet.add_task(t_skipped)
        pending = pet.get_pending_tasks()
        assert pending == [t_pending]

    def test_get_pending_tasks_empty_when_all_done(self):
        pet = make_pet("cat", "Luna", "p1")
        t = make_task("All done", "t1")
        t.complete()
        pet.add_task(t)
        assert pet.get_pending_tasks() == []

    def test_get_pending_tasks_empty_list(self):
        pet = make_pet("turtle", "Shelly", "p1")
        assert pet.get_pending_tasks() == []


# ===========================================================================
# 12. Plan class — add_pet, remove_pet, get_all_tasks
# ===========================================================================

class TestPlan:

    @pytest.fixture()
    def plan(self):
        return Plan(
            id="plan-1",
            name="Weekend Care",
            start_date=date(2026, 4, 4),
            end_date=date(2026, 4, 5),
        )

    @pytest.fixture()
    def pet_lookup(self):
        dog = make_pet("dog", "Rex", "p-dog")
        cat = make_pet("cat", "Luna", "p-cat")
        dog.add_task(make_task("Feed Rex", "t-dog"))
        cat.add_task(make_task("Feed Luna", "t-cat"))
        return {"p-dog": dog, "p-cat": cat}

    # --- add_pet ---

    def test_add_pet_id_appears_in_plan(self, plan):
        plan.add_pet("p-dog")
        assert "p-dog" in plan.pet_ids

    def test_add_multiple_pets(self, plan):
        plan.add_pet("p-dog")
        plan.add_pet("p-cat")
        assert len(plan.pet_ids) == 2

    def test_add_same_pet_twice_is_idempotent(self, plan):
        plan.add_pet("p-dog")
        plan.add_pet("p-dog")
        assert plan.pet_ids.count("p-dog") == 1

    # --- remove_pet ---

    def test_remove_pet_id_gone(self, plan):
        plan.add_pet("p-dog")
        plan.add_pet("p-cat")
        plan.remove_pet("p-dog")
        assert "p-dog" not in plan.pet_ids
        assert "p-cat" in plan.pet_ids

    def test_remove_nonexistent_pet_is_safe(self, plan):
        plan.add_pet("p-dog")
        plan.remove_pet("does-not-exist")
        assert len(plan.pet_ids) == 1

    def test_remove_all_pets_leaves_empty(self, plan):
        plan.add_pet("p-dog")
        plan.remove_pet("p-dog")
        assert plan.pet_ids == []

    # --- get_all_tasks ---

    def test_get_all_tasks_returns_tasks_for_enrolled_pets(self, plan, pet_lookup):
        plan.add_pet("p-dog")
        plan.add_pet("p-cat")
        tasks = plan.get_all_tasks(pet_lookup)
        descriptions = {t.description for t in tasks}
        assert descriptions == {"Feed Rex", "Feed Luna"}

    def test_get_all_tasks_count_matches(self, plan, pet_lookup):
        plan.add_pet("p-dog")
        tasks = plan.get_all_tasks(pet_lookup)
        assert len(tasks) == 1

    def test_get_all_tasks_ignores_unknown_pet_id(self, plan, pet_lookup):
        plan.add_pet("p-dog")
        plan.add_pet("p-unknown")
        tasks = plan.get_all_tasks(pet_lookup)
        assert len(tasks) == 1

    def test_get_all_tasks_empty_when_no_pets_enrolled(self, plan, pet_lookup):
        assert plan.get_all_tasks(pet_lookup) == []

    def test_get_all_tasks_empty_lookup(self, plan):
        plan.add_pet("p-dog")
        assert plan.get_all_tasks({}) == []


# ===========================================================================
# 13. Owner — add_plan, add_time_constraint, get_available_times
# ===========================================================================

class TestOwnerPlanAndConstraints:

    @pytest.fixture()
    def owner(self):
        return make_owner()

    # --- add_plan ---

    def test_add_plan_appears_in_plans(self, owner):
        plan = Plan("pl-1", "Week 1", date(2026, 4, 1), date(2026, 4, 7))
        owner.add_plan(plan)
        assert plan in owner.plans

    def test_add_multiple_plans(self, owner):
        owner.add_plan(Plan("pl-1", "Week 1", date(2026, 4,  1), date(2026, 4,  7)))
        owner.add_plan(Plan("pl-2", "Week 2", date(2026, 4,  8), date(2026, 4, 14)))
        assert len(owner.plans) == 2

    # --- add_time_constraint ---

    def test_add_time_constraint_appears_in_list(self, owner):
        constraint = TimeConstraint("Monday", time(9, 0), time(17, 0))
        owner.add_time_constraint(constraint)
        assert constraint in owner.time_constraints

    def test_add_multiple_constraints(self, owner):
        owner.add_time_constraint(TimeConstraint("Monday",    time(9, 0), time(17, 0)))
        owner.add_time_constraint(TimeConstraint("Wednesday", time(9, 0), time(12, 0)))
        assert len(owner.time_constraints) == 2

    # --- get_available_times ---

    def test_get_available_times_returns_matching_day(self, owner):
        mon = TimeConstraint("Monday", time(9, 0), time(17, 0))
        tue = TimeConstraint("Tuesday", time(10, 0), time(14, 0))
        owner.add_time_constraint(mon)
        owner.add_time_constraint(tue)
        result = owner.get_available_times("Monday")
        assert result == [mon]

    def test_get_available_times_multiple_windows_same_day(self, owner):
        am = TimeConstraint("Saturday", time(8, 0),  time(12, 0))
        pm = TimeConstraint("Saturday", time(14, 0), time(18, 0))
        owner.add_time_constraint(am)
        owner.add_time_constraint(pm)
        result = owner.get_available_times("Saturday")
        assert len(result) == 2
        assert am in result and pm in result

    def test_get_available_times_returns_empty_for_unknown_day(self, owner):
        owner.add_time_constraint(TimeConstraint("Monday", time(9, 0), time(17, 0)))
        assert owner.get_available_times("Sunday") == []

    def test_get_available_times_empty_when_no_constraints(self, owner):
        assert owner.get_available_times("Monday") == []


# ===========================================================================
# 14. Scheduler.filter_tasks() — status filter branch (line 225)
# ===========================================================================

class TestFilterTasksStatusBranch:
    """
    filter_tasks(status=...) must skip tasks whose status doesn't match.
    This exercises the `continue` branch at line 225 that was previously uncovered.
    """

    @pytest.fixture()
    def loaded_scheduler(self):
        owner = make_owner()
        pet = make_pet("dog", "Rex", "p1")
        t_pending   = make_task("Pending task",   "t1")
        t_completed = make_task("Completed task", "t2")
        t_skipped   = make_task("Skipped task",   "t3")
        t_in_prog   = make_task("In-progress",    "t4")
        t_completed.complete()
        t_skipped.skip()
        t_in_prog.start()
        for t in [t_pending, t_completed, t_skipped, t_in_prog]:
            pet.add_task(t)
        owner.add_pet(pet)
        return Scheduler(owner=owner)

    def test_filter_by_pending_excludes_others(self, loaded_scheduler):
        result = loaded_scheduler.filter_tasks(status=TaskStatus.PENDING)
        assert all(t.status == TaskStatus.PENDING for t in result)
        assert len(result) == 1
        assert result[0].description == "Pending task"

    def test_filter_by_completed_excludes_others(self, loaded_scheduler):
        result = loaded_scheduler.filter_tasks(status=TaskStatus.COMPLETED)
        assert all(t.status == TaskStatus.COMPLETED for t in result)
        assert len(result) == 1
        assert result[0].description == "Completed task"

    def test_filter_by_skipped_excludes_others(self, loaded_scheduler):
        result = loaded_scheduler.filter_tasks(status=TaskStatus.SKIPPED)
        assert len(result) == 1
        assert result[0].description == "Skipped task"

    def test_filter_by_in_progress_excludes_others(self, loaded_scheduler):
        result = loaded_scheduler.filter_tasks(status=TaskStatus.IN_PROGRESS)
        assert len(result) == 1
        assert result[0].description == "In-progress"

    def test_filter_no_status_returns_all(self, loaded_scheduler):
        result = loaded_scheduler.filter_tasks()
        assert len(result) == 4

    def test_filter_by_pet_name_and_status_combined(self, loaded_scheduler):
        result = loaded_scheduler.filter_tasks(pet_name="Rex", status=TaskStatus.PENDING)
        assert len(result) == 1
        assert result[0].description == "Pending task"

    def test_filter_by_wrong_pet_name_returns_empty(self, loaded_scheduler):
        result = loaded_scheduler.filter_tasks(pet_name="NotARealPet",
                                               status=TaskStatus.PENDING)
        assert result == []
