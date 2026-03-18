"""
Scenario Builder - Combine tasks into episodes
"""

import json
import streamlit as st
from pathlib import Path

st.title("🎬 Scenario Builder")
st.caption("Combine Tasks into a single Episode with sequential actions")

st.markdown("---")

# Saved tasks directory
TASKS_DIR = Path(__file__).parent.parent / "data" / "tasks" / "saved"
TASKS_DIR.mkdir(parents=True, exist_ok=True)

# Episodes output directory
EPISODES_DIR = Path(__file__).parent.parent / "data" / "episodes"
EPISODES_DIR.mkdir(parents=True, exist_ok=True)


def build_episode(tasks: list[dict], episode_config: dict) -> dict:
    """
    Build an episode JSON from a list of tasks.

    Each task's actions are combined into a single episode with:
    - Sequential action_ids
    - wait_for_action_ids linking to previous task's actions
    - bond_action_ids preserved for CONVERSATE+GAZE pairs
    """
    episode = {
        "app_id": episode_config.get("app_id", "episode"),
        "episode_id": episode_config.get("episode_id", "1"),
        "haru_id": episode_config.get("haru_id", "haru-jp"),
        "stage_id": episode_config.get("stage_id", 1),
        "task_id": episode_config.get("task_id", 1),
        "ready": False,
        "mute": True,
        "teleconference_on": True,
        "description": episode_config.get("description", "Generated Episode"),
        "actions": [],
    }

    current_action_id = 1
    prev_task_action_ids = []  # Track last task's action IDs for sequencing

    for task_idx, task in enumerate(tasks):
        task_data = task.get("data", task)
        task_actions = task_data.get("actions", [])

        # Map old action_ids to new ones for this task
        action_id_map = {}
        task_action_ids = []

        for action in task_actions:
            old_id = action.get("action_id", current_action_id)
            action_id_map[old_id] = current_action_id

            new_action = {
                "action_id": current_action_id,
                "action_type": action.get("action_type"),
            }

            # Handle wait_for_action_ids
            wait_ids = []

            # First, map any internal wait_for_action_ids from the task
            if "wait_for_action_ids" in action and action["wait_for_action_ids"]:
                mapped_waits = [
                    action_id_map.get(wid, wid)
                    for wid in action["wait_for_action_ids"]
                    if wid in action_id_map
                ]
                wait_ids.extend(mapped_waits)

            # Add cross-task linking: any root action (no internal waits)
            # in a subsequent task should wait for the previous task to finish
            if task_idx > 0 and prev_task_action_ids and not wait_ids:
                wait_ids = list(prev_task_action_ids)

            if wait_ids:
                new_action["wait_for_action_ids"] = wait_ids

            # Handle bond_action_ids (for GAZE actions paired with CONVERSATE)
            if "bond_action_ids" in action:
                new_action["bond_action_ids"] = [
                    action_id_map.get(bid, bid) for bid in action["bond_action_ids"]
                ]

            # Copy action_arguments
            if "action_arguments" in action:
                new_action["action_arguments"] = action["action_arguments"]

            # Copy action_goal
            if "action_goal" in action:
                new_action["action_goal"] = action["action_goal"]

            # Copy action_results_key
            if "action_results_key" in action:
                new_action["action_results_key"] = action["action_results_key"]

            # Copy action_content
            if "action_content" in action:
                new_action["action_content"] = action["action_content"]

            episode["actions"].append(new_action)
            task_action_ids.append(current_action_id)
            current_action_id += 1

        # Compute leaf actions: actions that no other action in this task
        # waits for. These are the "last" actions to finish.
        # Note: bond_action_ids are excluded — bonded actions finish together,
        # so the bonding target is still a leaf.
        depended_on = set()
        for action in task_actions:
            for wid in action.get("wait_for_action_ids", []) or []:
                if wid in action_id_map:
                    depended_on.add(action_id_map[wid])
        leaf_ids = [aid for aid in task_action_ids if aid not in depended_on]
        prev_task_action_ids = leaf_ids if leaf_ids else task_action_ids

    return episode


# Initialize session state for scenario
if "scenario_tasks" not in st.session_state:
    st.session_state["scenario_tasks"] = []

# Two-column layout
left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("📁 Available Tasks")

    # List saved task files
    task_files = list(TASKS_DIR.glob("*.json"))

    if not task_files:
        st.info("No saved tasks yet. Create tasks in the Task Builder page.")
        st.caption(f"Tasks are saved in: `{TASKS_DIR}`")
    else:
        for task_file in sorted(task_files):
            task_name = task_file.stem
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text(task_name)
            with col2:
                if st.button("➕", key=f"add_{task_name}", help="Add to scenario"):
                    # Load and add task
                    try:
                        with open(task_file) as f:
                            task_data = json.load(f)
                        st.session_state["scenario_tasks"].append({
                            "name": task_name,
                            "data": task_data,
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading task: {e}")
            with col3:
                if st.button("🗑️", key=f"delete_task_{task_name}", help="Delete task"):
                    task_file.unlink()
                    st.rerun()

    st.markdown("---")
    st.caption("💡 Create tasks in **Task Builder**, then add them here.")

with right_col:
    st.subheader("📋 Episode Builder")

    scenario_tasks = st.session_state["scenario_tasks"]

    if not scenario_tasks:
        st.markdown("""
        <div style="
            padding: 60px 40px;
            text-align: center;
            color: #999;
            background: #f9f9f9;
            border-radius: 12px;
            border: 2px dashed #ddd;
        ">
            <p style="font-size: 48px; margin: 0;">📋</p>
            <p style="margin: 16px 0 8px 0; font-size: 18px;">No tasks in episode</p>
            <p style="margin: 0; font-size: 14px;">Add tasks from the left panel to build your episode</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Display tasks in scenario order
        for idx, task in enumerate(scenario_tasks):
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 1, 1])

                with col1:
                    st.markdown(f"**{idx + 1}. {task['name']}**")
                    # Show action count
                    actions = task["data"].get("actions", [])
                    st.caption(f"{len(actions)} actions")

                with col2:
                    # Move up/down
                    if idx > 0:
                        if st.button("⬆️", key=f"up_{idx}", help="Move up"):
                            scenario_tasks[idx], scenario_tasks[idx - 1] = scenario_tasks[idx - 1], scenario_tasks[idx]
                            st.rerun()
                    if idx < len(scenario_tasks) - 1:
                        if st.button("⬇️", key=f"down_{idx}", help="Move down"):
                            scenario_tasks[idx], scenario_tasks[idx + 1] = scenario_tasks[idx + 1], scenario_tasks[idx]
                            st.rerun()

                with col3:
                    if st.button("🗑️", key=f"del_{idx}", help="Remove"):
                        scenario_tasks.pop(idx)
                        st.rerun()

            # Arrow between tasks
            if idx < len(scenario_tasks) - 1:
                st.markdown('<div style="text-align: center; color: #ccc; font-size: 20px;">↓</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Episode configuration
        st.subheader("Episode Settings")

        col1, col2 = st.columns(2)
        with col1:
            app_id = st.text_input("App ID", value="my_episode")
            episode_id = st.text_input("Episode ID", value="1")
            haru_id = st.selectbox("Haru ID", ["haru-jp", "haru-aus"], index=0)

        with col2:
            stage_id = st.number_input("Stage ID", value=1, min_value=1)
            task_id = st.number_input("Task ID", value=1, min_value=1)

        description = st.text_input(
            "Description",
            value=f"Episode with {len(scenario_tasks)} tasks: " + ", ".join(t["name"] for t in scenario_tasks[:3]) + ("..." if len(scenario_tasks) > 3 else ""),
        )

        st.markdown("---")

        # Build episode
        episode_config = {
            "app_id": app_id,
            "episode_id": episode_id,
            "haru_id": haru_id,
            "stage_id": stage_id,
            "task_id": task_id,
            "description": description,
        }

        episode_data = build_episode(scenario_tasks, episode_config)
        json_str = json.dumps(episode_data, indent=2, ensure_ascii=False)

        # Action summary
        total_actions = len(episode_data["actions"])
        st.info(f"Episode contains **{total_actions} actions** from {len(scenario_tasks)} tasks")

        # Export buttons
        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                "📥 Download Episode",
                data=json_str,
                file_name=f"{app_id}.json",
                mime="application/json",
                type="primary",
            )

        with col2:
            if st.button("💾 Save to Episodes", type="secondary"):
                save_path = EPISODES_DIR / f"{app_id}.json"
                with open(save_path, "w") as f:
                    json.dump(episode_data, f, indent=2, ensure_ascii=False)
                st.success(f"Saved to `{save_path}`")

        # Action flow visualization
        with st.expander("🔄 Action Flow", expanded=True):
            st.caption("⏳ waits for · ⚡ parallel with · 🔗 bonded to")
            st.markdown("")
            for action in episode_data["actions"]:
                action_id = action["action_id"]
                action_type = action["action_type"]

                # Build info line
                info_parts = []
                has_wait = "wait_for_action_ids" in action and action["wait_for_action_ids"]
                has_bond = "bond_action_ids" in action

                if has_wait:
                    info_parts.append(f"⏳ {action['wait_for_action_ids']}")
                elif action_id > 1 and not has_bond:
                    # Parallel with previous action (no wait, no bond)
                    info_parts.append(f"⚡ [{action_id - 1}]")

                if has_bond:
                    # Bonded actions run parallel with their bond
                    info_parts.append(f"⚡ {action['bond_action_ids']}")
                    info_parts.append(f"🔗 {action['bond_action_ids']}")

                info_str = f" ({', '.join(info_parts)})" if info_parts else ""

                # Icon based on action type (same as Task Builder)
                icon = {
                    "HARU_CONVERSATE": "💬",
                    "HARU_GAZE": "👁️",
                    "HARU_SHARE": "🖥️",
                    "HARU_REQUEST": "📥",
                }.get(action_type, "⚙️")

                st.markdown(f"**{icon} Action {action_id}**: {action_type}{info_str}")

        # Preview
        with st.expander("📄 Preview Episode JSON", expanded=False):
            st.code(json_str, language="json")

        # Clear button
        if st.button("🗑️ Clear Episode", type="secondary"):
            st.session_state["scenario_tasks"] = []
            st.rerun()

# Sidebar guide
with st.sidebar:
    st.markdown("### How to use")
    st.markdown("""
    1. Go to **Task Builder** page
    2. Create tasks from templates
    3. Click **Save** to save the task
    4. Return here to add tasks to episode
    5. **Reorder** tasks with ⬆️⬇️ buttons
    6. Configure **Episode Settings**
    7. **Download** the complete episode
    """)

