"""Action list viewer component."""

import streamlit as st
from ..services.session_manager import SessionManager


def render_action_list() -> None:
    """Render the list of current actions with edit/delete buttons."""
    actions = SessionManager.get_actions()

    st.subheader("Current Actions")

    if not actions:
        st.info("No actions added yet. Use the form below to add one.")
        return

    for idx, action in enumerate(actions):
        action_id = action.get("action_id", idx + 1)
        action_type = action.get("action_type", "Unknown")

        # Create a summary line
        summary_parts = [f"#{action_id} - {action_type}"]

        # Add relevant details based on type
        if action_type == "HARU_GAZE":
            args = action.get("action_arguments", {})
            gaze_args = args.get("gaze_arguments", {})
            if gaze_args:
                summary_parts.append(f"({gaze_args.get('gaze_mode', '')})")

        if action_type == "HARU_SHARE":
            args = action.get("action_arguments", {})
            share_args = args.get("share_arguments", {})
            if share_args:
                summary_parts.append(f"({share_args.get('share_type', '')})")

        if action.get("bond_action_ids"):
            summary_parts.append(f"[bonds: {action['bond_action_ids']}]")
        if action.get("wait_for_action_ids"):
            summary_parts.append(f"[waits: {action['wait_for_action_ids']}]")

        with st.expander(" ".join(summary_parts)):
            st.json(action)

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("Edit", key=f"edit_{idx}"):
                    SessionManager.set_editing_index(idx)
                    st.rerun()
            with col2:
                if st.button("Delete", key=f"delete_{idx}", type="secondary"):
                    SessionManager.delete_action(idx)
                    st.rerun()
            with col3:
                # Move up/down buttons
                col3a, col3b = st.columns(2)
                with col3a:
                    if idx > 0:
                        if st.button("↑", key=f"up_{idx}"):
                            actions[idx], actions[idx - 1] = (
                                actions[idx - 1],
                                actions[idx],
                            )
                            SessionManager.set_actions(actions)
                            st.rerun()
                with col3b:
                    if idx < len(actions) - 1:
                        if st.button("↓", key=f"down_{idx}"):
                            actions[idx], actions[idx + 1] = (
                                actions[idx + 1],
                                actions[idx],
                            )
                            SessionManager.set_actions(actions)
                            st.rerun()


def get_action_ids() -> list[int]:
    """Get list of all current action IDs for reference selection."""
    actions = SessionManager.get_actions()
    return [a.get("action_id", i + 1) for i, a in enumerate(actions)]
