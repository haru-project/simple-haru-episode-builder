
import streamlit as st
import json

st.set_page_config(page_title="Haru Episode JSON Builder", layout="wide")

# ---------- Session State Init ----------
if "actions" not in st.session_state:
    st.session_state.actions = []
if "editing_index" not in st.session_state:
    st.session_state.editing_index = None


# ---------- Helper Functions ----------
def parse_int_list(s: str):
    """Parse comma-separated integers like '1, 2,3' into [1,2,3]."""
    s = s.strip()
    if not s:
        return []
    try:
        return [int(x.strip()) for x in s.split(",") if x.strip()]
    except ValueError:
        st.warning("Could not parse integer list; please use comma-separated integers.")
        return []


def reset_action_form():
    st.session_state.editing_index = None


# ---------- Sidebar: Episode / Global Settings ----------
st.sidebar.header("Episode Metadata")

app_id = st.sidebar.text_input("app_id", value="test")
episode_id = st.sidebar.text_input("episode_id", value="1")
haru_id = st.sidebar.text_input("haru_id", value="haru-jp")
stage_id = st.sidebar.number_input("stage_id", min_value=0, value=1, step=1)
task_id = st.sidebar.number_input("task_id", min_value=0, value=1, step=1)

ready = st.sidebar.checkbox("ready", value=False)
mute = st.sidebar.checkbox("mute", value=True)
teleconference_on = st.sidebar.checkbox("teleconference_on", value=True)

description = st.sidebar.text_area("description", value="Test Interaction")


# ---------- Main Layout ----------
st.title("Haru Episode JSON Creator")

st.markdown(
    """
Use this app to build JSON episodes.  
1. Configure the metadata in the sidebar.  
2. Add actions below.  
3. Download the JSON file when you're done.
"""
)


# ---------- Existing Actions Viewer ----------
st.subheader("Current Actions")

if st.session_state.actions:
    for idx, a in enumerate(st.session_state.actions):
        with st.expander(f"Action #{a.get('action_id', idx+1)} – {a.get('action_type', '')}"):
            st.json(a)
            cols = st.columns(2)
            if cols[0].button("Edit", key=f"edit_{idx}"):
                st.session_state.editing_index = idx
            if cols[1].button("Delete", key=f"delete_{idx}"):
                st.session_state.actions.pop(idx)
                st.rerun()
else:
    st.info("No actions added yet. Use the form below to add one.")


# ---------- Action Form ----------
st.subheader("Add / Edit Action")

if st.session_state.actions:
    default_action_id = max(a["action_id"] for a in st.session_state.actions) + 1
else:
    default_action_id = 1
default_action_type = "HARU_CONVERSATE"
default_action_goal = ""
default_bond_ids = ""
default_wait_ids = ""

editing_idx = st.session_state.editing_index
editing_action = None

if editing_idx is not None and 0 <= editing_idx < len(st.session_state.actions):
    editing_action = st.session_state.actions[editing_idx]
    default_action_id = editing_action.get("action_id", default_action_id)
    default_action_type = editing_action.get("action_type", default_action_type)
    default_action_goal = editing_action.get("action_goal", default_action_goal)
    default_bond_ids = ", ".join(str(i) for i in editing_action.get("bond_action_ids", []))
    default_wait_ids = ", ".join(str(i) for i in editing_action.get("wait_for_action_ids", []))

ACTION_TYPES = ["HARU_CONVERSATE", "HARU_GAZE"]

with st.form(key="action_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        action_id = st.number_input("action_id", min_value=1, value=int(default_action_id), step=1)
        # Selectbox for limited action types
        default_index = ACTION_TYPES.index(default_action_type) if default_action_type in ACTION_TYPES else 0
        action_type = st.selectbox("action_type", ACTION_TYPES, index=default_index)
    with col2:
        bond_ids_str = st.text_input(
            "bond_action_ids (comma-separated)", 
            value=default_bond_ids,
            help="e.g.: 1,3,4"
        )
        wait_ids_str = st.text_input(
            "wait_for_action_ids (comma-separated)", 
            value=default_wait_ids,
            help="e.g.: 2,5"
        )

    action_goal = st.text_area(
        "action_goal (optional)",
        value=default_action_goal,
        help="Useful for HARU_CONVERSATE goals / success / termination.",
    )

    # Explain fixed behavior depending on action_type
    if action_type == "HARU_GAZE":
        st.markdown(
            """
**HARU_GAZE behavior**

For `HARU_GAZE`, `action_arguments` will always be set to:

```json
{
  "gaze_arguments": {
    "gaze_mode": "TRACK_PERSON"
  }
}
```

`action_content` will remain `[]`.
"""
        )
    else:
        st.markdown(
            """
**HARU_CONVERSATE behavior**

For `HARU_CONVERSATE`, `action_content` will be `[]`  
and no `action_arguments` will be added for now.
"""
        )

    submitted = st.form_submit_button("Save Action")
    cancel_edit = st.form_submit_button("Cancel Edit")

    if cancel_edit:
        reset_action_form()
        st.rerun()

    if submitted:
        bond_ids = parse_int_list(bond_ids_str)
        wait_ids = parse_int_list(wait_ids_str)

        # Base action structure
        action_dict = {
            "action_id": int(action_id),
            "action_type": action_type,
            "action_content": [],
        }

        # Optional fields
        if action_goal.strip():
            action_dict["action_goal"] = action_goal
        if bond_ids:
            action_dict["bond_action_ids"] = bond_ids
        if wait_ids:
            action_dict["wait_for_action_ids"] = wait_ids

        # Fixed action_arguments for HARU_GAZE
        if action_type == "HARU_GAZE":
            action_dict["action_arguments"] = {
                "gaze_arguments": {
                    "gaze_mode": "TRACK_PERSON"
                }
            }

        if editing_action is not None:
            st.session_state.actions[editing_idx] = action_dict
            st.success(f"Updated action with id {action_id}.")
        else:
            st.session_state.actions.append(action_dict)
            st.success(f"Added action with id {action_id}.")

        reset_action_form()
        st.rerun()


# ---------- JSON Preview & Download ----------
st.subheader("Generated JSON Preview")

episode_json = {
    "app_id": app_id,
    "episode_id": episode_id,
    "haru_id": haru_id,
    "stage_id": int(stage_id),
    "task_id": int(task_id),
    "ready": bool(ready),
    "mute": bool(mute),
    "teleconference_on": bool(teleconference_on),
    "description": description,
    "actions": st.session_state.actions,
}

st.code(json.dumps(episode_json, indent=4), language="json")

st.download_button(
    label="Download JSON file",
    data=json.dumps(episode_json, indent=4),
    file_name=f"episode_{episode_id}.json",
    mime="application/json",
)
