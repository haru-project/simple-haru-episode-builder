"""
Scenario Builder - Combine tasks into scenarios
"""

import json
import streamlit as st
from pathlib import Path

st.title("🎬 Scenario Builder")
st.caption("A Scenario is a sequence of Tasks")

st.markdown("---")

# Saved tasks directory
TASKS_DIR = Path(__file__).parent.parent / "data" / "tasks" / "saved"
TASKS_DIR.mkdir(parents=True, exist_ok=True)

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
    st.subheader("📋 Scenario")

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
            <p style="margin: 16px 0 8px 0; font-size: 18px;">No tasks in scenario</p>
            <p style="margin: 0; font-size: 14px;">Add tasks from the left panel to build your scenario</p>
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

        # Export scenario
        col1, col2 = st.columns(2)

        with col1:
            scenario_name = st.text_input("Scenario Name", value="my_scenario")

        with col2:
            st.markdown("")  # Spacer
            st.markdown("")

            # Build scenario JSON
            scenario_data = {
                "scenario_name": scenario_name,
                "tasks": [task["data"] for task in scenario_tasks],
            }

            json_str = json.dumps(scenario_data, indent=2, ensure_ascii=False)

            st.download_button(
                "📥 Download Scenario",
                data=json_str,
                file_name=f"{scenario_name}.json",
                mime="application/json",
                type="primary",
            )

        # Preview
        with st.expander("📄 Preview JSON"):
            st.code(json_str, language="json")

        # Clear button
        if st.button("🗑️ Clear Scenario", type="secondary"):
            st.session_state["scenario_tasks"] = []
            st.rerun()

# Sidebar guide
with st.sidebar:
    st.markdown("### How to use")
    st.markdown("""
    1. Go to **Task Builder** page
    2. Create tasks from templates
    3. Click **Save** to save the task
    4. Return here to add tasks to scenario
    5. **Reorder** tasks with ⬆️⬇️ buttons
    6. **Download** the complete scenario
    """)
