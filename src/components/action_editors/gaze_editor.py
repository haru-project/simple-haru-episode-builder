"""Editor for HARU_GAZE actions."""

import streamlit as st
from ..content_editor import render_content_editor
from ...utils.constants import GAZE_MODES


def render_gaze_editor(editing_action: dict | None = None) -> dict:
    """
    Render HARU_GAZE specific fields.

    Returns dict with gaze-specific field values.
    """
    st.markdown("---")
    st.markdown("### HARU_GAZE Configuration")

    # Get defaults from editing action
    default_gaze_mode = "TRACK_PERSON"
    default_content = []
    default_goal = ""

    if editing_action and editing_action.get("action_type") == "HARU_GAZE":
        args = editing_action.get("action_arguments", {})
        gaze_args = args.get("gaze_arguments", {})
        default_gaze_mode = gaze_args.get("gaze_mode", "TRACK_PERSON")
        default_content = editing_action.get("action_content", [])
        default_goal = editing_action.get("action_goal", "")

    # Gaze mode selector
    gaze_mode = st.selectbox(
        "Gaze Mode",
        options=GAZE_MODES,
        index=GAZE_MODES.index(default_gaze_mode) if default_gaze_mode in GAZE_MODES else 0,
        key="gaze_mode",
        help="TRACK_PERSON: Follow individual(s). GROUP: Look at the group as a whole.",
    )

    # Optional goal for gaze
    with st.expander("Action Goal (optional)", expanded=bool(default_goal)):
        st.caption("Use a goal to let the AI decide who to gaze at based on context.")
        action_goal = st.text_area(
            "Goal",
            value=default_goal,
            height=60,
            key="gaze_goal",
            placeholder="e.g., Gaze at the person right in front of you.",
        )

    # Content editor
    st.markdown("#### Gaze Content")
    st.caption(
        "Leave empty for AI-controlled gaze, or specify explicit targets. "
        "For bonded gaze actions, content is often empty."
    )
    action_content = render_content_editor(
        "HARU_GAZE",
        default_content,
        key_prefix="gaze_content",
    )

    result = {
        "action_arguments": {
            "gaze_arguments": {
                "gaze_mode": gaze_mode
            }
        },
        "action_content": action_content if action_content else [],
    }

    if action_goal and action_goal.strip():
        result["action_goal"] = action_goal

    return result


def reset_gaze_editor_state():
    """Reset gaze editor session state."""
    keys_to_reset = [k for k in st.session_state.keys() if k.startswith("gaze_")]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
