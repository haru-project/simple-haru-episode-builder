"""Editor for HARU_CONVERSATE actions."""

import streamlit as st
from ..goal_editor import render_goal_editor, reset_goal_editor_state
from ..content_editor import render_content_editor


def render_conversate_editor(editing_action: dict | None = None) -> dict:
    """
    Render HARU_CONVERSATE specific fields.

    Returns dict with conversate-specific field values.
    """
    st.markdown("---")
    st.markdown("### HARU_CONVERSATE Configuration")

    # Get defaults from editing action
    default_goal = ""
    default_content = []
    if editing_action and editing_action.get("action_type") == "HARU_CONVERSATE":
        default_goal = editing_action.get("action_goal", "")
        default_content = editing_action.get("action_content", [])

    # Goal editor
    st.markdown("#### Action Goal")
    action_goal = render_goal_editor(default_goal)

    # Content editor (usually empty for CONVERSATE with goals)
    with st.expander("Action Content (optional)", expanded=bool(default_content)):
        st.caption(
            "For goal-based conversations, content is typically empty. "
            "Use content for scripted TTS sequences."
        )
        action_content = render_content_editor(
            "HARU_CONVERSATE",
            default_content,
            key_prefix="conversate_content",
        )

    return {
        "action_goal": action_goal if action_goal else None,
        "action_content": action_content if action_content else [],
    }


def reset_conversate_editor_state():
    """Reset conversate editor session state."""
    reset_goal_editor_state()
    # Reset content editor state
    keys_to_reset = [k for k in st.session_state.keys() if k.startswith("conversate_content")]
    for key in keys_to_reset:
        del st.session_state[key]
