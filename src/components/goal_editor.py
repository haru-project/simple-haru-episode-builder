"""Structured goal editor component for HARU_CONVERSATE actions."""

import json
import streamlit as st
from ..models.goal import ActionGoal, SuccessCriterion, CriteriaExpand, CriteriaExpandMapping, Timeout
PARTICIPANT_SOURCES = ["participants", "participants_start_left", "participants_start_right"]


def render_goal_editor(current_goal: str = "") -> str | None:
    """
    Render a structured goal editor.

    Args:
        current_goal: Current goal string (may be plain text or JSON)

    Returns:
        Updated goal string, or None if using plain text mode
    """
    # Try to parse current goal as structured JSON
    parsed_goal = None
    if current_goal and current_goal.strip().startswith("{"):
        try:
            parsed_goal = ActionGoal.from_json_string(current_goal)
        except Exception:
            pass

    # Mode selection
    use_structured = st.checkbox(
        "Use Structured Goal Editor",
        value=parsed_goal is not None,
        help="Enable structured editing of goal with success criteria, timeout, etc.",
    )

    if not use_structured:
        # Plain text mode
        plain_goal = st.text_area(
            "Goal (plain text)",
            value=current_goal if parsed_goal is None else "",
            height=100,
            help="Enter a simple text goal or paste JSON directly",
        )
        return plain_goal

    # Structured mode
    st.markdown("---")
    st.markdown("### Goal Configuration")

    # Initialize from parsed or defaults
    if parsed_goal:
        default_id = parsed_goal.id
        default_desc = parsed_goal.description
        default_criteria = parsed_goal.success_criteria
        default_expand = parsed_goal.criteria_expand
        default_timeout = parsed_goal.timeout
        default_instructions = parsed_goal.additional_instructions
    else:
        default_id = "goal_1"
        default_desc = ""
        default_criteria = []
        default_expand = []
        default_timeout = None
        default_instructions = []

    # Basic info
    col1, col2 = st.columns(2)
    with col1:
        goal_id = st.text_input("Goal ID", value=default_id)
    with col2:
        pass  # Reserved for future use

    goal_description = st.text_area(
        "Goal Description",
        value=default_desc,
        height=60,
        help="Main description of what this goal achieves",
    )

    # Success Criteria
    st.markdown("#### Success Criteria")

    # Initialize criteria in session state
    criteria_key = "goal_editor_criteria"
    if criteria_key not in st.session_state:
        st.session_state[criteria_key] = [
            {"id": c.id, "description": c.description} for c in default_criteria
        ] if default_criteria else []

    criteria_list = st.session_state[criteria_key]

    # Display existing criteria
    for i, criterion in enumerate(criteria_list):
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            criteria_list[i]["id"] = st.text_input(
                "ID", value=criterion["id"], key=f"crit_id_{i}", label_visibility="collapsed"
            )
        with col2:
            criteria_list[i]["description"] = st.text_input(
                "Description",
                value=criterion["description"],
                key=f"crit_desc_{i}",
                label_visibility="collapsed",
                placeholder="Criterion description (use {participant}, {robot_name}, etc.)",
            )
        with col3:
            if st.button("✕", key=f"del_crit_{i}"):
                criteria_list.pop(i)
                st.rerun()

    # Add criterion button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("+ Add Criterion"):
            next_id = f"c{len(criteria_list) + 1}"
            criteria_list.append({"id": next_id, "description": ""})
            st.rerun()

    # Criteria Expand (for participant variables)
    st.markdown("#### Criteria Expansion")
    st.caption("Map participant variables to criteria (e.g., expand criteria for each participant)")

    expand_key = "goal_editor_expand"
    if expand_key not in st.session_state:
        st.session_state[expand_key] = [
            {
                "ids": exp.ids,
                "source": exp.mappings[0].source if exp.mappings else "",
                "target": exp.mappings[0].target if exp.mappings else "",
            }
            for exp in default_expand
        ] if default_expand else []

    expand_list = st.session_state[expand_key]

    for i, expand in enumerate(expand_list):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            # Multi-select for criterion IDs
            available_ids = [c["id"] for c in criteria_list]
            expand_list[i]["ids"] = st.multiselect(
                "Criteria IDs",
                options=available_ids,
                default=[id_ for id_ in expand["ids"] if id_ in available_ids],
                key=f"exp_ids_{i}",
                label_visibility="collapsed",
            )
        with col2:
            expand_list[i]["source"] = st.selectbox(
                "Source",
                options=PARTICIPANT_SOURCES,
                index=PARTICIPANT_SOURCES.index(expand["source"]) if expand["source"] in PARTICIPANT_SOURCES else 0,
                key=f"exp_src_{i}",
                label_visibility="collapsed",
            )
        with col3:
            expand_list[i]["target"] = st.text_input(
                "Target",
                value=expand["target"],
                key=f"exp_tgt_{i}",
                label_visibility="collapsed",
                placeholder="participant",
            )
        with col4:
            if st.button("✕", key=f"del_exp_{i}"):
                expand_list.pop(i)
                st.rerun()

    if st.button("+ Add Expansion"):
        expand_list.append({"ids": [], "source": PARTICIPANT_SOURCES[0], "target": "participant"})
        st.rerun()

    # Timeout
    st.markdown("#### Timeout")
    col1, col2, col3 = st.columns(3)
    with col1:
        timeout_minutes = st.number_input(
            "Minutes",
            min_value=0,
            value=default_timeout.max_time.get("minutes", 0) if default_timeout and default_timeout.max_time else 5,
            step=1,
        )
    with col2:
        timeout_seconds = st.number_input(
            "Seconds",
            min_value=0,
            max_value=59,
            value=default_timeout.max_time.get("seconds", 0) if default_timeout and default_timeout.max_time else 0,
            step=1,
        )
    with col3:
        max_turns = st.number_input(
            "Max Turns (optional)",
            min_value=0,
            value=default_timeout.max_turns if default_timeout and default_timeout.max_turns else 0,
            step=1,
            help="0 = no limit",
        )

    # Additional Instructions
    st.markdown("#### Additional Instructions")

    instructions_key = "goal_editor_instructions"
    if instructions_key not in st.session_state:
        st.session_state[instructions_key] = default_instructions if default_instructions else []

    instructions_list = st.session_state[instructions_key]

    for i, instruction in enumerate(instructions_list):
        col1, col2 = st.columns([10, 1])
        with col1:
            instructions_list[i] = st.text_input(
                f"Instruction {i + 1}",
                value=instruction,
                key=f"instr_{i}",
                label_visibility="collapsed",
            )
        with col2:
            if st.button("✕", key=f"del_instr_{i}"):
                instructions_list.pop(i)
                st.rerun()

    if st.button("+ Add Instruction"):
        instructions_list.append("")
        st.rerun()

    # Build the goal object
    success_criteria = [
        SuccessCriterion(id=c["id"], description=c["description"], reached=False, evidence=None)
        for c in criteria_list
        if c["id"] and c["description"]
    ]

    criteria_expand = [
        CriteriaExpand(
            ids=exp["ids"],
            mappings=[CriteriaExpandMapping(source=exp["source"], target=exp["target"])]
        )
        for exp in expand_list
        if exp["ids"] and exp["source"] and exp["target"]
    ]

    timeout = Timeout.create(
        minutes=int(timeout_minutes),
        seconds=int(timeout_seconds),
        max_turns=int(max_turns) if max_turns > 0 else None,
    )

    additional_instructions = [i for i in instructions_list if i.strip()]

    goal = ActionGoal(
        id=goal_id,
        description=goal_description,
        success_criteria=success_criteria,
        criteria_expand=criteria_expand,
        timeout=timeout if (timeout_minutes > 0 or timeout_seconds > 0 or max_turns > 0) else None,
        additional_instructions=additional_instructions,
    )

    # Preview
    with st.expander("Preview Goal JSON"):
        st.code(json.dumps(json.loads(goal.to_json_string()), indent=2), language="json")

    return goal.to_json_string()


def reset_goal_editor_state():
    """Reset goal editor session state."""
    keys_to_reset = ["goal_editor_criteria", "goal_editor_expand", "goal_editor_instructions"]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
