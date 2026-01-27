"""Base action editor with common fields."""

import streamlit as st
from ...utils.helpers import parse_int_list
from ...utils.constants import ACTION_TYPES
from ...services.session_manager import SessionManager


def render_base_action_fields(
    editing_action: dict | None = None,
    default_action_id: int = 1,
) -> dict:
    """
    Render common action fields (id, type, bond/wait IDs).

    Returns dict with base field values.
    """
    # Defaults from editing action if provided
    if editing_action:
        default_action_id = editing_action.get("action_id", default_action_id)
        default_action_type = editing_action.get("action_type", "HARU_CONVERSATE")
        default_bond_ids = ", ".join(
            str(i) for i in editing_action.get("bond_action_ids", [])
        )
        default_wait_ids = ", ".join(
            str(i) for i in editing_action.get("wait_for_action_ids", [])
        )
    else:
        default_action_type = "HARU_CONVERSATE"
        default_bond_ids = ""
        default_wait_ids = ""

    col1, col2 = st.columns(2)

    with col1:
        action_id = st.number_input(
            "Action ID",
            min_value=1,
            value=int(default_action_id),
            step=1,
            key="base_action_id",
        )

        default_index = (
            ACTION_TYPES.index(default_action_type)
            if default_action_type in ACTION_TYPES
            else 0
        )
        action_type = st.selectbox(
            "Action Type",
            ACTION_TYPES,
            index=default_index,
            key="base_action_type",
        )

    with col2:
        bond_ids_str = st.text_input(
            "Bond Action IDs (comma-separated)",
            value=default_bond_ids,
            help="Actions that run in parallel with this one (e.g., 1, 3, 4)",
            key="base_bond_ids",
        )
        wait_ids_str = st.text_input(
            "Wait For Action IDs (comma-separated)",
            value=default_wait_ids,
            help="Actions that must complete before this one starts (e.g., 2, 5)",
            key="base_wait_ids",
        )

    return {
        "action_id": int(action_id),
        "action_type": action_type,
        "bond_action_ids": parse_int_list(bond_ids_str),
        "wait_for_action_ids": parse_int_list(wait_ids_str),
    }


def get_next_action_id() -> int:
    """Get the next available action ID."""
    actions = SessionManager.get_actions()
    if not actions:
        return 1
    return max(a.get("action_id", 0) for a in actions) + 1
