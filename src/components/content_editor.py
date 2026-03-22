"""Content editor component for action_content field."""

import json
import streamlit as st
from ..utils.constants import CONTENT_TYPES_BY_ACTION


def render_content_editor(
    action_type: str,
    current_content: list | str = None,
    key_prefix: str = "content",
) -> list | str:
    """
    Render content editor appropriate for the action type.

    Args:
        action_type: The type of action (HARU_CONVERSATE, HARU_GAZE, etc.)
        current_content: Current content value
        key_prefix: Prefix for widget keys

    Returns:
        Updated content list or string
    """
    if current_content is None:
        current_content = []

    # Check if content is a template reference (string like "{{var}}")
    if isinstance(current_content, str):
        st.info("Content is a template reference")
        return st.text_input(
            "Template Reference",
            value=current_content,
            key=f"{key_prefix}_template_ref",
            help="e.g., {{local_avatars_results}}",
        )

    content_types = CONTENT_TYPES_BY_ACTION.get(action_type, [])

    if action_type == "HARU_CONVERSATE":
        return _render_conversate_content(current_content, key_prefix)
    elif action_type == "HARU_GAZE":
        return _render_gaze_content(current_content, key_prefix)
    elif action_type == "HARU_SHARE":
        return _render_share_content(current_content, key_prefix)
    elif action_type == "HARU_REQUEST":
        return _render_request_content(current_content, key_prefix)
    else:
        # Generic JSON editor
        return _render_generic_content(current_content, key_prefix)


def _render_conversate_content(content: list, key_prefix: str) -> list:
    """Render content editor for HARU_CONVERSATE."""
    st.markdown("##### Action Content")

    # Initialize in session state
    content_key = f"{key_prefix}_items"
    if content_key not in st.session_state:
        st.session_state[content_key] = content if content else []

    items = st.session_state[content_key]

    result = []
    for i, item in enumerate(items):
        with st.expander(f"Content Item {i + 1}", expanded=True):
            value_type = st.selectbox(
                "Content Type",
                options=CONTENT_TYPES_BY_ACTION["HARU_CONVERSATE"],
                index=0 if item.get("value_type") not in CONTENT_TYPES_BY_ACTION["HARU_CONVERSATE"]
                else CONTENT_TYPES_BY_ACTION["HARU_CONVERSATE"].index(item.get("value_type", "JSON_CONVERSATE_MULTITTS")),
                key=f"{key_prefix}_{i}_type",
            )

            metainfo = st.text_input(
                "Metainfo",
                value=item.get("metainfo", ""),
                key=f"{key_prefix}_{i}_meta",
            )

            if value_type == "JSON_CONVERSATE_MULTITTS":
                # TTS entries editor
                tts_entries = item.get("value", [])
                if not isinstance(tts_entries, list):
                    tts_entries = []

                st.markdown("**TTS Entries:**")
                new_entries = []
                for j, entry in enumerate(tts_entries):
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        tts_text = st.text_input(
                            "TTS",
                            value=entry.get("tts", ""),
                            key=f"{key_prefix}_{i}_tts_{j}",
                            label_visibility="collapsed",
                        )
                    with col2:
                        delay = st.number_input(
                            "Delay",
                            value=entry.get("delay", 1.0),
                            min_value=0.0,
                            step=0.5,
                            key=f"{key_prefix}_{i}_delay_{j}",
                            label_visibility="collapsed",
                        )
                    with col3:
                        routine = st.number_input(
                            "Routine",
                            value=entry.get("routine", 0),
                            min_value=0,
                            key=f"{key_prefix}_{i}_routine_{j}",
                            label_visibility="collapsed",
                        )
                    if tts_text:
                        entry_dict = {"tts": tts_text, "delay": delay}
                        if routine > 0:
                            entry_dict["routine"] = routine
                        new_entries.append(entry_dict)

                if st.button("+ Add TTS Entry", key=f"{key_prefix}_{i}_add_tts"):
                    tts_entries.append({"tts": "", "delay": 1, "routine": 0})
                    items[i]["value"] = tts_entries
                    st.rerun()

                result.append({
                    "value": new_entries,
                    "value_type": value_type,
                    "metainfo": metainfo,
                })
            else:
                # Generic value editor for other types
                value_json = st.text_area(
                    "Value (JSON)",
                    value=json.dumps(item.get("value", []), indent=2),
                    key=f"{key_prefix}_{i}_value",
                    height=100,
                )
                try:
                    value = json.loads(value_json)
                except json.JSONDecodeError:
                    value = []
                    st.warning("Invalid JSON")

                result.append({
                    "value": value,
                    "value_type": value_type,
                    "metainfo": metainfo,
                })

            if st.button("Remove", key=f"{key_prefix}_{i}_remove"):
                items.pop(i)
                st.rerun()

    if st.button("+ Add Content Item", key=f"{key_prefix}_add"):
        items.append({"value": [], "value_type": "JSON_CONVERSATE_MULTITTS", "metainfo": ""})
        st.rerun()

    return result if result else []


def _render_gaze_content(content: list, key_prefix: str) -> list:
    """Render content editor for HARU_GAZE."""
    st.markdown("##### Gaze Content")

    content_type = st.selectbox(
        "Gaze Content Type",
        options=["(empty)", "GAZE_INDIVIDUAL", "JSON_GAZE_MULTI_INDIVIDUAL", "GAZE_STOP"],
        key=f"{key_prefix}_gaze_type",
    )

    if content_type == "(empty)":
        return []

    if content_type == "GAZE_STOP":
        metainfo = st.text_input("Metainfo", value="Stop gaze tracking", key=f"{key_prefix}_stop_meta")
        return [{"value_type": "GAZE_STOP", "metainfo": metainfo}]

    if content_type == "GAZE_INDIVIDUAL":
        st.markdown("**Target User:**")
        col1, col2 = st.columns(2)
        with col1:
            haru_id = st.text_input("Haru ID", value="haru-jp", key=f"{key_prefix}_gaze_haru")
        with col2:
            local_id = st.number_input("Local ID", value=1, min_value=-1, key=f"{key_prefix}_gaze_local")
        metainfo = st.text_input("Metainfo", value="", key=f"{key_prefix}_gaze_meta")
        return [{
            "user_id": {"haru_id": haru_id, "local_id": int(local_id)},
            "value_type": "GAZE_INDIVIDUAL",
            "metainfo": metainfo,
        }]

    if content_type == "JSON_GAZE_MULTI_INDIVIDUAL":
        st.markdown("**Gaze Targets:**")

        targets_key = f"{key_prefix}_gaze_targets"
        if targets_key not in st.session_state:
            # Try to extract from existing content
            if content and isinstance(content, list) and content:
                existing_value = content[0].get("value", {})
                if isinstance(existing_value, dict):
                    st.session_state[targets_key] = existing_value.get("gaze_targets", [])
                else:
                    st.session_state[targets_key] = []
            else:
                st.session_state[targets_key] = []

        targets = st.session_state[targets_key]

        new_targets = []
        for i, target in enumerate(targets):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                user_id = st.text_input(
                    "User ID",
                    value=target.get("user_id", "1"),
                    key=f"{key_prefix}_tgt_{i}_uid",
                    label_visibility="collapsed",
                )
            with col2:
                duration = st.number_input(
                    "Duration (ms)",
                    value=target.get("duration", 5000),
                    min_value=0,
                    step=1000,
                    key=f"{key_prefix}_tgt_{i}_dur",
                    label_visibility="collapsed",
                )
            with col3:
                if st.button("✕", key=f"{key_prefix}_tgt_{i}_del"):
                    targets.pop(i)
                    st.rerun()
            new_targets.append({"user_id": user_id, "duration": int(duration)})

        if st.button("+ Add Target", key=f"{key_prefix}_add_tgt"):
            targets.append({"user_id": str(len(targets) + 1), "duration": 5000})
            st.rerun()

        loop = st.checkbox("Loop through targets", key=f"{key_prefix}_gaze_loop")
        metainfo = st.text_input("Metainfo", value="", key=f"{key_prefix}_multi_meta")

        return [{
            "value": {"gaze_targets": new_targets, "loop": loop},
            "value_type": "JSON_GAZE_MULTI_INDIVIDUAL",
            "metainfo": metainfo,
        }]

    return []


def _render_share_content(content: list, key_prefix: str) -> list:
    """Render content editor for HARU_SHARE."""
    st.markdown("##### Share Content")

    # Determine if using template reference
    use_template = st.checkbox(
        "Use template reference",
        value=False,
        key=f"{key_prefix}_share_use_template",
        help="Reference results from a previous REQUEST action",
    )

    if use_template:
        template_ref = st.text_input(
            "Template Reference",
            value="{{results}}",
            key=f"{key_prefix}_share_template",
            help="e.g., {{avatars}}, {{drawings}}",
        )
        return template_ref

    content_type = st.selectbox(
        "Share Content Type",
        options=CONTENT_TYPES_BY_ACTION["HARU_SHARE"],
        key=f"{key_prefix}_share_type",
    )

    value = st.text_input(
        "Value (URL or text)",
        value=content[0].get("value", "") if content else "",
        key=f"{key_prefix}_share_value",
    )

    metainfo = st.text_input(
        "Metainfo",
        value=content[0].get("metainfo", "") if content else "",
        key=f"{key_prefix}_share_meta",
    )

    if value:
        return [{
            "value": value,
            "value_type": content_type,
            "metainfo": metainfo,
        }]
    return []


def _render_request_content(content: list, key_prefix: str) -> list:
    """Render content editor for HARU_REQUEST."""
    st.markdown("##### Request Content")
    st.markdown("**Target User:**")

    # Extract existing values
    existing = content[0] if content else {}
    existing_user = existing.get("user_id", {})

    col1, col2 = st.columns(2)
    with col1:
        haru_id = st.text_input(
            "Haru ID",
            value=existing_user.get("haru_id", "haru-jp"),
            key=f"{key_prefix}_req_haru",
        )
    with col2:
        local_id = st.number_input(
            "Local ID (-1 for all)",
            value=existing_user.get("local_id", -1),
            min_value=-1,
            key=f"{key_prefix}_req_local",
        )

    metainfo = st.text_input(
        "Metainfo",
        value=existing.get("metainfo", ""),
        key=f"{key_prefix}_req_meta",
    )

    return [{
        "user_id": {"haru_id": haru_id, "local_id": int(local_id)},
        "metainfo": metainfo,
    }]


def _render_generic_content(content: list, key_prefix: str) -> list:
    """Render generic JSON content editor."""
    st.markdown("##### Content (JSON)")

    content_json = st.text_area(
        "Content JSON",
        value=json.dumps(content, indent=2) if content else "[]",
        height=150,
        key=f"{key_prefix}_generic",
    )

    try:
        return json.loads(content_json)
    except json.JSONDecodeError:
        st.warning("Invalid JSON")
        return []
