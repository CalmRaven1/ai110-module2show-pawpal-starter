import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# --- Session state init ---
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="", available_minutes=60)

# --- Header ---
st.title("🐾 PawPal+")

# ── Owner Info ────────────────────────────────────────────
st.subheader("Owner Info")
col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value=st.session_state.owner.name or "Jordan")
with col2:
    available = st.number_input("Available minutes today", min_value=10, max_value=480,
                                value=st.session_state.owner.available_minutes)

if st.button("Save owner info"):
    st.session_state.owner.name = owner_name
    st.session_state.owner.set_availability(available)
    st.success(f"Saved! Owner: {owner_name}, {available} min available.")

st.divider()

# ── Add a Pet ─────────────────────────────────────────────
st.subheader("Add a Pet")
col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with col3:
    age = st.number_input("Age", min_value=0, max_value=30, value=2)

if st.button("Add pet"):
    existing_names = [p.name for p in st.session_state.owner.pets]
    if pet_name in existing_names:
        st.warning(f"{pet_name} is already added.")
    else:
        st.session_state.owner.add_pet(Pet(name=pet_name, species=species, age=int(age)))
        st.success(f"Added: {pet_name} the {species}.")

# Pet list with remove button
if st.session_state.owner.pets:
    st.markdown("**Your pets:**")
    for p in st.session_state.owner.pets:
        col_info, col_remove = st.columns([4, 1])
        with col_info:
            st.markdown(f"- {p.name} ({p.species}, age {p.age})")
        with col_remove:
            if st.button("Remove", key=f"remove_pet_{p.name}"):
                st.session_state.owner.remove_pet(p.name)
                st.rerun()

st.divider()

# ── Add / Manage Tasks ────────────────────────────────────
st.subheader("Add a Task")

if not st.session_state.owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    pet_names = [p.name for p in st.session_state.owner.pets]
    selected_pet_name = st.selectbox("Assign task to", pet_names)
    selected_pet = next(p for p in st.session_state.owner.pets if p.name == selected_pet_name)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col4, col5, col6 = st.columns(3)
    with col4:
        category = st.selectbox("Category", ["walk", "feeding", "meds", "grooming", "enrichment"])
    with col5:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])
    with col6:
        time_slot = st.selectbox("Time slot", ["morning", "afternoon", "evening", "anytime"])

    if st.button("Add task"):
        selected_pet.add_task(Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=priority,
            category=category,
            frequency=frequency,
            time_slot=time_slot,
        ))
        st.success(f"Added '{task_title}' to {selected_pet_name}.")

    # ── Filters ───────────────────────────────────────────
    st.markdown("**Filter tasks:**")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        pet_filter = st.selectbox(
            "Pet", ["All"] + pet_names, key="filter_pet"
        )
    with col_f2:
        status_filter = st.selectbox(
            "Status", ["All", "Pending", "Completed"], key="filter_status"
        )

    pet_arg = None if pet_filter == "All" else pet_filter
    status_arg = None if status_filter == "All" else status_filter.lower()
    visible_tasks = st.session_state.owner.filter_tasks(pet_arg, status_arg)

    # ── Task table with complete / delete per row ──────────
    if visible_tasks:
        st.markdown("**Tasks:**")
        for pet, task in visible_tasks:
            col_info, col_due, col_done, col_del = st.columns([5, 1, 1, 1])
            with col_info:
                strike = "~~" if task.completed else ""
                slot_label = f" `{task.time_slot}`" if task.time_slot != "anytime" else ""
                st.markdown(
                    f"{strike}**[{task.priority.upper()}]** {pet.name}: {task.title} "
                    f"({task.duration_minutes} min, {task.frequency}){slot_label}{strike}"
                )
            with col_due:
                if not task.completed:
                    due_label = "due" if task.is_due_today() else "not due"
                    st.caption(due_label)
            with col_done:
                label = "Undo" if task.completed else "Done"
                if st.button(label, key=f"done_{pet.name}_{task.title}"):
                    if task.completed:
                        pet.undo_complete(task.title)
                    else:
                        pet.complete_task(task.title)
                    st.rerun()
            with col_del:
                if st.button("Delete", key=f"del_{pet.name}_{task.title}"):
                    pet.remove_task(task.title)
                    st.rerun()
    else:
        st.info("No tasks match the current filter.")

st.divider()

# ── Generate Schedule ─────────────────────────────────────
st.subheader("Generate Today's Schedule")

if st.button("Generate schedule"):
    if not st.session_state.owner.name:
        st.warning("Please save owner info first.")
    elif not st.session_state.owner.pets:
        st.warning("Add at least one pet first.")
    elif not st.session_state.owner.get_all_pending_tasks():
        st.warning("No pending tasks to schedule. Add tasks or undo completed ones.")
    else:
        scheduler = Scheduler(st.session_state.owner)
        schedule = scheduler.generate()

        st.success(f"Schedule for {st.session_state.owner.name} — {schedule.date}")
        st.markdown(f"**Total time:** {schedule.total_duration} min "
                    f"/ {st.session_state.owner.available_minutes} min available")

        # Conflicts banner
        for conflict in schedule.conflicts:
            st.warning(f"⚠️ Conflict: {conflict}")

        PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        SLOT_ICON = {"morning": "🌅", "afternoon": "☀️", "evening": "🌙", "anytime": ""}
        for pet, task in schedule.planned_tasks:
            icon = PRIORITY_ICON.get(task.priority, "")
            slot_icon = SLOT_ICON.get(task.time_slot, "")
            st.markdown(
                f"{icon}{slot_icon} **{task.title}** — {task.duration_minutes} min "
                f"`[{pet.name}]` _{task.frequency}_"
            )

        st.info(schedule.explanation)
