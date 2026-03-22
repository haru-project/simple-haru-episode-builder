"""Sidebar metadata form component."""

import streamlit as st
from ..services.session_manager import SessionManager


def render_metadata_sidebar() -> dict:
    """Render the sidebar metadata form and return current values."""
    SessionManager.initialize()
    metadata = SessionManager.get_metadata()

    st.sidebar.header("Episode Metadata")

    app_id = st.sidebar.text_input("app_id", value=metadata.get("app_id", "test"))
    episode_id = st.sidebar.text_input(
        "episode_id", value=metadata.get("episode_id", "1")
    )
    haru_id = st.sidebar.text_input("haru_id", value=metadata.get("haru_id", "haru-jp"))
    stage_id = st.sidebar.number_input(
        "stage_id", min_value=0, value=metadata.get("stage_id", 1), step=1
    )
    task_id = st.sidebar.number_input(
        "task_id", min_value=0, value=metadata.get("task_id", 1), step=1
    )

    ready = st.sidebar.checkbox("ready", value=metadata.get("ready", False))
    mute = st.sidebar.checkbox("mute", value=metadata.get("mute", True))
    teleconference_on = st.sidebar.checkbox(
        "teleconference_on", value=metadata.get("teleconference_on", True)
    )

    description = st.sidebar.text_area(
        "description", value=metadata.get("description", "")
    )

    # Update session state
    new_metadata = {
        "app_id": app_id,
        "episode_id": episode_id,
        "haru_id": haru_id,
        "stage_id": int(stage_id),
        "task_id": int(task_id),
        "ready": bool(ready),
        "mute": bool(mute),
        "teleconference_on": bool(teleconference_on),
        "description": description,
    }

    # Only update if changed to avoid unnecessary reruns
    if new_metadata != metadata:
        SessionManager.update_metadata(**new_metadata)

    return new_metadata
