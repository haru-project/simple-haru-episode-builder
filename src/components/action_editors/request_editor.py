"""Editor for HARU_REQUEST actions."""

import streamlit as st
from ..content_editor import render_content_editor
from ...utils.constants import REQUEST_TYPES


def render_request_editor(editing_action: dict | None = None) -> dict:
    """
    Render HARU_REQUEST specific fields.

    Returns dict with request-specific field values.
    """
    st.markdown("---")
    st.markdown("### HARU_REQUEST Configuration")

    # Get defaults from editing action
    default_request_type = "IMAGE_AVATAR"
    default_results_key = ""
    default_content = []

    if editing_action and editing_action.get("action_type") == "HARU_REQUEST":
        args = editing_action.get("action_arguments", {})
        request_args = args.get("request_arguments", {})
        default_request_type = request_args.get("request_type", default_request_type)
        default_results_key = editing_action.get("action_results_key", "")
        default_content = editing_action.get("action_content", [])

    # Request type
    col1, col2 = st.columns(2)

    with col1:
        request_type = st.selectbox(
            "Request Type",
            options=REQUEST_TYPES,
            index=REQUEST_TYPES.index(default_request_type) if default_request_type in REQUEST_TYPES else 0,
            key="request_type",
            help="Type of content to request from users",
        )

    with col2:
        results_key = st.text_input(
            "Results Key",
            value=default_results_key,
            key="request_results_key",
            help="Key to store results (e.g., 'local_avatars_results'). Can be referenced in later SHARE actions.",
            placeholder="local_avatars_results",
        )

    # Content editor (user targeting)
    st.markdown("#### Request Content")
    st.caption("Specify which user(s) to request content from.")
    action_content = render_content_editor(
        "HARU_REQUEST",
        default_content,
        key_prefix="request_content",
    )

    result = {
        "action_arguments": {
            "request_arguments": {
                "request_type": request_type
            }
        },
        "action_content": action_content if action_content else [],
    }

    if results_key and results_key.strip():
        result["action_results_key"] = results_key

    return result


def reset_request_editor_state():
    """Reset request editor session state."""
    keys_to_reset = [k for k in st.session_state.keys() if k.startswith("request_")]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
