"""
Task Builder - Create individual tasks from templates
"""

import json
import re
import streamlit as st
from pathlib import Path

from src.services.template_service import TemplateService
from src.utils.constants import DEFAULT_TEMPLATE_PATH

# Saved tasks directory
SAVED_TASKS_DIR = Path(__file__).parent.parent / "data" / "tasks" / "saved"

# ---------------------------------------------------------------------------
# Block templates — extensible: add entries here for new block types
# ---------------------------------------------------------------------------
VOICE_GENRES = ["default", "question", "highnrg", "sad", "serious", "whiny"]

BLOCK_TEMPLATES = {
    "Express TTS": {
        "action_type": "HARU_CONVERSATE",
        "fields": [
            {"name": "tts", "label": "TTS Text", "type": "text_area", "required": True,
             "help": "The robot's speech text."},
            {"name": "voice_genre", "label": "Voice Genre", "type": "select", "default": "default",
             "options": VOICE_GENRES,
             "help": "Voice style: default (neutral), question (interrogative), highnrg (energetic), sad, serious, whiny (frustrated)."},
            {"name": "delay", "label": "Delay (seconds)", "type": "number", "default": 0,
             "help": "Delay in seconds between the TTS and the routine."},
            {"name": "routine", "label": "Routine ID", "type": "number", "default": 2001,
             "help": "Routine ID from the [Routine List](https://docs.google.com/spreadsheets/d/1HAl8e7q3Vk94xx7pFC_rzmOrMwwRwDomXYbhDgINVmE/edit?gid=0#gid=0)."},
            {"name": "metainfo", "label": "Metainfo", "type": "text", "default": ""},
        ],
        "build": lambda vals: {
            "action_type": "HARU_CONVERSATE",
            "action_content": [
                {
                    "value": [
                        {
                            "tts": f'<usel genre="{vals["voice_genre"]}"> {vals["tts"]} </usel>',
                            "delay": vals["delay"],
                            "routine": vals["routine"],
                        }
                    ],
                    "value_type": "JSON_CONVERSATE_MULTITTS",
                    "metainfo": vals["metainfo"] if vals.get("metainfo") else "Express TTS",
                }
            ],
        },
    },
}


ACTION_KEY_ORDER = [
    "action_id", "wait_for_action_ids", "bond_action_ids",
    "action_type", "action_arguments", "action_goal", "action_content",
]


def _order_action_keys(action: dict) -> dict:
    """Return a new dict with keys in the canonical order."""
    ordered = {}
    for key in ACTION_KEY_ORDER:
        if key in action:
            ordered[key] = action[key]
    # Append any extra keys not in the standard order
    for key in action:
        if key not in ordered:
            ordered[key] = action[key]
    return ordered


def prepare_for_save(task: dict) -> dict:
    """Return a copy of the task with action keys in canonical order."""
    out = dict(task)
    out["actions"] = [_order_action_keys(a) for a in task.get("actions", [])]
    return out


def renumber_actions(actions: list) -> list:
    """Renumber action IDs sequentially and update all references."""
    old_to_new = {}
    for idx, action in enumerate(actions):
        old_id = action.get("action_id", idx + 1)
        new_id = idx + 1
        old_to_new[old_id] = new_id
        action["action_id"] = new_id

    for action in actions:
        if "wait_for_action_ids" in action and action["wait_for_action_ids"]:
            action["wait_for_action_ids"] = [
                old_to_new[wid] for wid in action["wait_for_action_ids"] if wid in old_to_new
            ]
        if "bond_action_ids" in action and action["bond_action_ids"]:
            action["bond_action_ids"] = [
                old_to_new[bid] for bid in action["bond_action_ids"] if bid in old_to_new
            ]
    return actions


def _get_bond_group(actions: list, action_id: int) -> set[int]:
    """Return the set of action IDs bonded with action_id (including itself)."""
    group = {action_id}
    for a in actions:
        aid = a.get("action_id", 0)
        bonds = a.get("bond_action_ids", [])
        if aid == action_id or action_id in bonds:
            group.add(aid)
            group.update(bonds)
    return group


def insert_action(task: dict, target_action_id: int, position: str, new_action_data: dict):
    """Insert a new action before or after target_action_id and rewire dependencies.

    Bonded actions (e.g. CONVERSATE + GAZE) are treated as a group:
    - "before": new action inherits the group's wait_for_action_ids;
      all actions in the group now wait for the new action.
    - "after": new action waits for all actions in the group;
      any action that waited for any member of the group now waits for the new action.
    """
    actions = task.get("actions", [])
    actions = sorted(actions, key=lambda a: a.get("action_id", 0))

    target_idx = next(
        (i for i, a in enumerate(actions) if a.get("action_id") == target_action_id), None
    )
    if target_idx is None:
        return

    # Identify bond group by old IDs (before any mutation)
    old_bond_group = _get_bond_group(actions, target_action_id)
    # Track group members by list index so we survive renumbering
    group_member_indices = [i for i, a in enumerate(actions) if a.get("action_id") in old_bond_group]

    if position == "before":
        insert_idx = min(group_member_indices)

        # Collect external wait_for_action_ids from the group
        group_waits = set()
        for gi in group_member_indices:
            for wid in actions[gi].get("wait_for_action_ids", []):
                if wid not in old_bond_group:
                    group_waits.add(wid)
        new_action_data["wait_for_action_ids"] = list(group_waits)

        actions.insert(insert_idx, new_action_data)
        # Indices shifted +1 for everything at or after insert_idx
        group_member_indices = [gi + 1 for gi in group_member_indices]

        renumber_actions(actions)
        new_id = actions[insert_idx]["action_id"]

        # Group members' new IDs (after renumber)
        group_new_ids = {actions[gi]["action_id"] for gi in group_member_indices}

        # All group members: keep intra-group waits, add wait for new action
        for gi in group_member_indices:
            a = actions[gi]
            old_waits = a.get("wait_for_action_ids", [])
            kept = [wid for wid in old_waits if wid in group_new_ids]
            if new_id not in kept:
                kept.append(new_id)
            a["wait_for_action_ids"] = kept

    else:  # after
        insert_idx = max(group_member_indices) + 1

        actions.insert(insert_idx, new_action_data)
        # Group indices are all before insert_idx, so they don't shift

        renumber_actions(actions)
        new_id = actions[insert_idx]["action_id"]

        # Group members' new IDs (after renumber)
        group_new_ids = {actions[gi]["action_id"] for gi in group_member_indices}

        # New action waits for all members of the bond group
        actions[insert_idx]["wait_for_action_ids"] = sorted(group_new_ids)

        # Any non-group action that waited for a group member now waits for the new action
        for i, a in enumerate(actions):
            if i == insert_idx or i in group_member_indices:
                continue
            waits = a.get("wait_for_action_ids", [])
            if any(wid in group_new_ids for wid in waits):
                replaced = [new_id if wid in group_new_ids else wid for wid in waits]
                seen = set()
                a["wait_for_action_ids"] = [w for w in replaced if w not in seen and not seen.add(w)]

    task["actions"] = actions


def delete_action(task: dict, action_id: int):
    """Remove an action and rewire dependencies so the flow stays connected."""
    actions = task.get("actions", [])
    actions = sorted(actions, key=lambda a: a.get("action_id", 0))

    target_idx = next(
        (i for i, a in enumerate(actions) if a.get("action_id") == action_id), None
    )
    if target_idx is None:
        return

    removed = actions[target_idx]
    removed_waits = removed.get("wait_for_action_ids", [])

    # Any action that waited for the removed action now inherits its wait_for_action_ids
    for a in actions:
        waits = a.get("wait_for_action_ids", [])
        if action_id in waits:
            new_waits = [wid for wid in waits if wid != action_id] + removed_waits
            # Deduplicate while preserving order
            seen = set()
            deduped = []
            for wid in new_waits:
                if wid not in seen:
                    seen.add(wid)
                    deduped.append(wid)
            a["wait_for_action_ids"] = deduped

    # Remove bond references to the deleted action
    for a in actions:
        bonds = a.get("bond_action_ids", [])
        if action_id in bonds:
            a["bond_action_ids"] = [bid for bid in bonds if bid != action_id]
            if not a["bond_action_ids"]:
                del a["bond_action_ids"]

    actions.pop(target_idx)
    renumber_actions(actions)
    task["actions"] = actions


def to_snake_case(text: str) -> str:
    """Convert text to snake_case identifier."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


def to_title_case(snake_text: str) -> str:
    """Convert snake_case to Title_Case (preserving underscores)."""
    return "_".join(word.capitalize() for word in snake_text.split("_"))


def get_action_content_preview(action: dict, max_len: int = 50) -> str:
    """Extract a short content preview for display in action flow."""
    atype = action.get("action_type", "").replace("HARU_", "")
    content = action.get("action_content", [])

    if atype == "CONVERSATE":
        goal_str = action.get("action_goal", "")
        if goal_str and goal_str.strip().startswith("{"):
            try:
                goal = json.loads(goal_str)
                desc = goal.get("description", "")
                if desc:
                    return desc[:max_len] + "..." if len(desc) > max_len else desc
            except json.JSONDecodeError:
                pass
        if goal_str:
            return goal_str[:max_len] + "..." if len(goal_str) > max_len else goal_str

    elif atype == "GAZE":
        args = action.get("action_arguments", {}).get("gaze_arguments", {})
        mode = args.get("gaze_mode", "")
        if mode:
            return f"Mode: {mode}"

    elif atype == "SHARE":
        args = action.get("action_arguments", {}).get("share_arguments", {})
        share_type = args.get("share_type", "")
        if content and isinstance(content, list):
            for c in content:
                val = c.get("value", "")
                if val:
                    preview = val[:max_len] + "..." if len(val) > max_len else val
                    return f"{share_type}: {preview}" if share_type else preview
        if share_type:
            return f"Type: {share_type}"

    elif atype == "REQUEST":
        args = action.get("action_arguments", {}).get("request_arguments", {})
        req_type = args.get("request_type", "")
        if req_type:
            return f"Request: {req_type}"

    return ""


def render_action_flow(actions: list):
    """Render interactive action flow with clickable boxes and side panel."""
    actions = sorted(actions, key=lambda a: a.get("action_id", 0))

    icons = {
        "CONVERSATE": "💬",
        "GAZE": "👁️",
        "SHARE": "🖥️",
        "REQUEST": "📥",
    }

    # Find parallel groups
    parallel_groups = {}
    for action in actions:
        aid = action.get("action_id", 0)
        bond_ids = action.get("bond_action_ids", [])
        if bond_ids:
            group_key = tuple(sorted([aid] + bond_ids))
            parallel_groups[group_key] = parallel_groups.get(group_key, set()) | {aid} | set(bond_ids)

    in_parallel = set()
    for group in parallel_groups.values():
        in_parallel.update(group)

    # Build display order
    display_items = []
    seen = set()

    for action in actions:
        aid = action.get("action_id", 0)
        if aid in seen:
            continue

        if aid in in_parallel:
            for group in parallel_groups.values():
                if aid in group:
                    group_actions = [a for a in actions if a.get("action_id") in group]
                    group_actions = sorted(group_actions, key=lambda a: a.get("action_id", 0))
                    display_items.append(group_actions)
                    seen.update(group)
                    break
        else:
            display_items.append([action])
            seen.add(aid)

    # Custom CSS
    st.markdown("""
    <style>
    .flow-arrow {
        text-align: center;
        color: #ccc;
        font-size: 18px;
        margin: 2px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Two-column layout
    flow_col, panel_col = st.columns([1, 2])

    with flow_col:
        for item_idx, item in enumerate(display_items):
            is_parallel = len(item) > 1

            if item_idx > 0:
                st.markdown('<div class="flow-arrow">↓</div>', unsafe_allow_html=True)

            if is_parallel:
                with st.container(border=True):
                    st.caption("⚡ Parallel")
                    for action in item:
                        aid = action.get("action_id", 0)
                        atype = action.get("action_type", "UNKNOWN").replace("HARU_", "")
                        icon = icons.get(atype, "📦")
                        selected = st.session_state.get("selected_action") == aid

                        if st.button(
                            f"{icon}  #{aid} {atype}",
                            key=f"btn_{aid}",
                            use_container_width=True,
                            type="primary" if selected else "secondary",
                        ):
                            st.session_state["selected_action"] = aid
                            st.rerun()

                        content_preview = get_action_content_preview(action)
                        if content_preview:
                            st.caption(content_preview)
            else:
                for action in item:
                    aid = action.get("action_id", 0)
                    atype = action.get("action_type", "UNKNOWN").replace("HARU_", "")
                    icon = icons.get(atype, "📦")
                    selected = st.session_state.get("selected_action") == aid

                    if st.button(
                        f"{icon}  #{aid} {atype}",
                        key=f"btn_{aid}",
                        use_container_width=True,
                        type="primary" if selected else "secondary",
                    ):
                        st.session_state["selected_action"] = aid
                        st.rerun()

                    content_preview = get_action_content_preview(action)
                    if content_preview:
                        st.caption(content_preview)

    with panel_col:
        selected_aid = st.session_state.get("selected_action")
        if selected_aid:
            selected_action = next((a for a in actions if a.get("action_id") == selected_aid), None)
            if selected_action:
                render_action_panel(selected_action)
        else:
            st.markdown("""
            <div style="
                padding: 40px;
                text-align: center;
                color: #999;
                background: #f9f9f9;
                border-radius: 12px;
                margin-top: 20px;
            ">
                <p style="font-size: 32px; margin: 0;">👈</p>
                <p style="margin: 8px 0 0 0;">Select an action to view details</p>
            </div>
            """, unsafe_allow_html=True)


def render_action_panel(action: dict):
    """Render details panel for selected action (Notion-like)."""
    aid = action.get("action_id", 0)
    atype = action.get("action_type", "UNKNOWN").replace("HARU_", "")

    colors = {
        "CONVERSATE": "#4CAF50",
        "GAZE": "#2196F3",
        "SHARE": "#FF9800",
        "REQUEST": "#9C27B0",
    }
    icons = {
        "CONVERSATE": "💬",
        "GAZE": "👁️",
        "SHARE": "🖥️",
        "REQUEST": "📥",
    }

    color = colors.get(atype, "#666")
    icon = icons.get(atype, "📦")

    st.markdown(f"""
    <div style="
        border-left: 4px solid {color};
        padding-left: 16px;
        margin-bottom: 16px;
    ">
        <h2 style="margin: 0; color: {color};">{icon} Action #{aid}</h2>
        <p style="margin: 4px 0 0 0; color: #666;">{atype}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Optional: Insert / Delete ---
    insert_mode = st.session_state.get("insert_mode")
    expander_open = insert_mode is not None and insert_mode[1] == aid
    with st.expander("➕ Insert or Delete Action", expanded=expander_open):
        btn_cols = st.columns(3)
        with btn_cols[0]:
            if st.button("⬆️ Insert Before", key=f"ins_before_{aid}", use_container_width=True):
                st.session_state["insert_mode"] = ("before", aid)
                st.rerun()
        with btn_cols[1]:
            if st.button("⬇️ Insert After", key=f"ins_after_{aid}", use_container_width=True):
                st.session_state["insert_mode"] = ("after", aid)
                st.rerun()
        with btn_cols[2]:
            if st.button("🗑️ Delete", key=f"del_action_{aid}", use_container_width=True):
                task = st.session_state.get("working_task")
                if task:
                    delete_action(task, aid)
                    st.session_state["selected_action"] = None
                    st.session_state.pop("insert_mode", None)
                    st.rerun()

        # --- Block insertion form ---
        if insert_mode and insert_mode[1] == aid:
            position, _ = insert_mode
            pos_label = "Before" if position == "before" else "After"
            st.markdown(f"#### Insert {pos_label} Action #{aid}")

            # Filter templates to those matching the selected action's type
            current_action_type = action.get("action_type", "")
            compatible = {
                name: tmpl for name, tmpl in BLOCK_TEMPLATES.items()
                if tmpl["action_type"] == current_action_type
            }
            if not compatible:
                st.info("No block templates available for this action type.")
            else:
                block_type = st.selectbox(
                    "Block Type",
                    options=list(compatible.keys()),
                    key=f"block_type_{aid}",
                )
                tmpl = compatible[block_type]
                field_values = {}
                for field in tmpl["fields"]:
                    fkey = f"block_field_{aid}_{field['name']}"
                    help_text = field.get("help")
                    if field["type"] == "text_area":
                        field_values[field["name"]] = st.text_area(
                            field["label"], key=fkey, help=help_text,
                        )
                    elif field["type"] == "number":
                        field_values[field["name"]] = st.number_input(
                            field["label"], value=field.get("default", 0), key=fkey, help=help_text,
                        )
                    elif field["type"] == "select":
                        options = field.get("options", [])
                        default_idx = options.index(field["default"]) if field.get("default") in options else 0
                        field_values[field["name"]] = st.selectbox(
                            field["label"], options=options, index=default_idx, key=fkey, help=help_text,
                        )
                    else:
                        field_values[field["name"]] = st.text_input(
                            field["label"], value=field.get("default", ""), key=fkey, help=help_text,
                        )

                form_cols = st.columns(2)
                with form_cols[0]:
                    can_confirm = all(
                        field_values.get(f["name"])
                        for f in tmpl["fields"]
                        if f.get("required")
                    )
                    if st.button(
                        "✅ Confirm", key=f"confirm_insert_{aid}",
                        disabled=not can_confirm, use_container_width=True,
                    ):
                        task = st.session_state.get("working_task")
                        if task:
                            new_action_data = tmpl["build"](field_values)
                            insert_action(task, aid, position, new_action_data)
                            st.session_state.pop("insert_mode", None)
                            st.session_state["selected_action"] = None
                            st.rerun()
                with form_cols[1]:
                    if st.button("Cancel", key=f"cancel_insert_{aid}", use_container_width=True):
                        st.session_state.pop("insert_mode", None)
                        st.rerun()

    wait_ids = action.get("wait_for_action_ids", [])
    bond_ids = action.get("bond_action_ids", [])

    if wait_ids or bond_ids:
        cols = st.columns(2)
        if wait_ids:
            with cols[0]:
                st.markdown(f"⏳ **Waits for:** `{', '.join(map(str, wait_ids))}`")
        if bond_ids:
            with cols[1]:
                st.markdown(f"⚡ **Parallel:** `{', '.join(map(str, bond_ids))}`")
        st.markdown("")

    with st.container(border=True):
        if atype == "CONVERSATE":
            goal = action.get("action_goal", "")
            render_goal_visualization(goal, action=action, action_id=aid, task_name=selected_name)

        elif atype == "GAZE":
            args = action.get("action_arguments", {}).get("gaze_arguments", {})
            st.markdown("#### 🎯 Gaze Mode")
            st.code(args.get("gaze_mode", "N/A"))

            content = action.get("action_content", [])
            if content and content != [{}]:
                st.markdown("#### 📍 Targets")
                st.json(content)

        elif atype == "SHARE":
            args = action.get("action_arguments", {}).get("share_arguments", {})

            st.markdown("#### ⚙️ Settings")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Type", args.get("share_type", "N/A"))
                st.metric("Mode", args.get("share_mode", "N/A"))
            with col2:
                st.metric("Screen", args.get("share_screen", "N/A"))
                st.metric("Subtype", args.get("share_subtype", "N/A"))

            video_args = args.get("share_video_args", {})
            if video_args:
                st.markdown("#### 🎬 Video Options")
                vcols = st.columns(3)
                vcols[0].checkbox("Loop", value=video_args.get("video_loop", False), disabled=True)
                vcols[1].checkbox("Mute", value=video_args.get("video_mute", False), disabled=True)
                vcols[2].checkbox("Wait", value=video_args.get("video_wait_completion", False), disabled=True)

            content = action.get("action_content", [])
            if content:
                st.markdown("#### 📄 Content")
                if isinstance(content, str):
                    st.code(content)
                elif isinstance(content, list) and content:
                    for c in content:
                        val = c.get("value", "")
                        vtype = c.get("value_type", "")
                        if val:
                            st.text_input(vtype, value=val, disabled=True)

        elif atype == "REQUEST":
            args = action.get("action_arguments", {}).get("request_arguments", {})

            st.markdown("#### 📋 Request Details")
            st.metric("Request Type", args.get("request_type", "N/A"))

            results_key = action.get("action_results_key", "")
            if results_key:
                st.text_input("Results Key", value=results_key, disabled=True)

            content = action.get("action_content", [])
            if content:
                st.markdown("#### 👥 Target Users")
                for c in content:
                    user = c.get("user_id", {})
                    col1, col2 = st.columns(2)
                    col1.text_input("Haru ID", value=user.get("haru_id", ""), disabled=True, key=f"usr_{aid}_haru")
                    col2.text_input("Local ID", value=str(user.get("local_id", "")), disabled=True, key=f"usr_{aid}_local")

    with st.expander("🔧 Raw JSON"):
        st.json(action)

def timeout_block(action: dict, goal: dict, timeout: dict, timeout_parent: dict, id: str, title: str = "Timeout") -> None:
    """Render editable timeout block with minutes, seconds, and max turns."""
    
    def update_timeout():
        """Update the timeout in the goal and action based on session state inputs."""
        mins = st.session_state[mins_key]
        secs = st.session_state[secs_key]
        turns = st.session_state[turns_key]

        new_timeout = {}

        if mins > 0 or secs > 0:
            new_timeout["max_time"] = {"minutes": mins, "seconds": secs}

        if turns > 0:
            new_timeout["max_turns"] = turns

        timeout_parent["timeout"] = new_timeout

        if action is not None:
            action["action_goal"] = json.dumps(goal, ensure_ascii=False)
    
    max_time = timeout.get("max_time", {})

    mins_key = f"timeout_mins_{task_name}_{id}"
    secs_key = f"timeout_secs_{task_name}_{id}"
    turns_key = f"timeout_turns_{task_name}_{id}"

    # Initialize session state if needed
    if mins_key not in st.session_state:
        st.session_state[mins_key] = max_time.get("minutes", 0)

    if secs_key not in st.session_state:
        st.session_state[secs_key] = max_time.get("seconds", 0)

    if turns_key not in st.session_state:
        st.session_state[turns_key] = timeout.get("max_turns", 0) or 0

    with st.expander(f"⏱️ {title}", expanded=bool(timeout)):

        col1, col2, col3 = st.columns(3)

        with col1:
            st.number_input(
                "Minutes",
                min_value=0,
                key=mins_key,
                on_change=update_timeout,
            )

        with col2:
            st.number_input(
                "Seconds",
                min_value=0,
                max_value=59,
                key=secs_key,
                on_change=update_timeout,
            )

        with col3:
            st.number_input(
                "Max Turns",
                min_value=0,
                key=turns_key,
                on_change=update_timeout,
            )

def render_goal_visualization(goal_str: str, action: dict = None, action_id: int = 0, task_name: str = ""):
    """Render a structured goal in a nice format with editable instructions and timeout."""
    if not goal_str or not goal_str.strip().startswith("{"):
        st.markdown(f"**Goal:** {goal_str}" if goal_str else "*No goal*")
        return

    try:
        goal = json.loads(goal_str)
    except json.JSONDecodeError:
        st.markdown(f"**Goal:** {goal_str}")
        return

    st.markdown(f"**{goal.get('description', 'Goal')}**")

    criteria = goal.get("success_criteria", [])
    criteria_expand = goal.get("criteria_expand", [])

    # Build set of expanded criteria IDs for marking
    expanded_ids = set()
    for exp in criteria_expand:
        expanded_ids.update(exp.get("ids", []))

    if criteria:
        st.markdown("**Success Criteria:**")
        for c in criteria:
            cid = c.get("id", "")
            desc = c.get("description", "")
            criteria_timeout = c.get("timeout", {})
            expand_marker = " 🔄" if cid in expanded_ids else ""
            st.markdown(f"- `{cid}`{expand_marker}: {desc}")
            timeout_block(action, goal, criteria_timeout, c, id=cid, title=f"Timeout for Criterion `{cid}`")


    # Show criteria expansion info
    if criteria_expand:
        with st.expander("🔄 Criteria Expansion", expanded=True):
            for exp in criteria_expand:
                ids = exp.get("ids", [])
                mappings = exp.get("mappings", [])
                ids_str = ", ".join(ids)
                for mapping in mappings:
                    source_var = mapping.get("source", "")
                    target_var = mapping.get("target", "")
                    st.markdown(f"**{ids_str}** → expand `{{{target_var}}}` for each value in `{source_var}`")

    # Editable timeout
    timeout = goal.get("timeout", {})
    timeout_block(action, goal, timeout, goal, action_id, title="Goal Timeout")

    # Editable additional instructions as list
    instructions = goal.get("additional_instructions", [])

    # Initialize session state for instructions list (include task_name to reset on template change)
    instr_key = f"instructions_list_{task_name}_{action_id}"
    if instr_key not in st.session_state:
        st.session_state[instr_key] = instructions.copy()

    with st.expander("✏️ Additional Instructions", expanded=bool(instructions)):
        current_instructions = st.session_state[instr_key]

        # Display each instruction with delete button
        to_delete = None
        for idx, instr in enumerate(current_instructions):
            col1, col2 = st.columns([5, 1])
            with col1:
                new_val = st.text_input(
                    f"Instruction {idx + 1}",
                    value=instr,
                    key=f"instr_{task_name}_{action_id}_{idx}",
                    label_visibility="collapsed",
                )
                if new_val != instr:
                    current_instructions[idx] = new_val
            with col2:
                if st.button("🗑️", key=f"del_instr_{task_name}_{action_id}_{idx}", help="Delete"):
                    to_delete = idx

        if to_delete is not None:
            current_instructions.pop(to_delete)
            st.session_state[instr_key] = current_instructions
            st.rerun()

        # Add new instruction
        col1, col2 = st.columns([5, 1])
        with col1:
            new_instr = st.text_input(
                "New instruction",
                value="",
                key=f"new_instr_{task_name}_{action_id}",
                placeholder="Add new instruction...",
                label_visibility="collapsed",
            )
        with col2:
            if st.button("➕", key=f"add_instr_{task_name}_{action_id}", help="Add"):
                if new_instr.strip():
                    current_instructions.append(new_instr.strip())
                    st.session_state[instr_key] = current_instructions
                    st.rerun()

        # Update action if instructions changed
        if action is not None and current_instructions != instructions:
            goal["additional_instructions"] = current_instructions
            action["action_goal"] = json.dumps(goal, ensure_ascii=False)


# Page content
st.title("📝 Task Builder")
st.caption("Create or edit tasks")

# Directories
template_path = DEFAULT_TEMPLATE_PATH
template_path.mkdir(parents=True, exist_ok=True)

template_service = TemplateService(template_path)
templates = template_service.list_templates()

# Load section
st.markdown("---")
st.subheader("Load")
source_tab1, source_tab2 = st.tabs(["📄 From Template", "📂 Load Existing"])

result = None
selected_name = None

with source_tab1:
    if not templates:
        st.warning("No templates found")
    else:
        # Create display labels with description only
        def format_template_option(t):
            if t.description:
                return t.description
            return t.name

        template_options = [format_template_option(t) for t in templates]
        template_map = {format_template_option(t): t for t in templates}

        # Searchable selectbox with empty default
        selected_label = st.selectbox(
            "🔍 Select Template",
            options=template_options,
            index=None,
            placeholder="Search or select a template...",
        )

        if selected_label:
            selected_template = template_map[selected_label]
            selected_name = selected_template.name

            template_data = template_service.load_template(selected_template.path)
            parameters = selected_template.parameters

            if parameters:
                st.markdown("---")
                st.subheader("Configure")

                template_base_name = selected_name  # Save original template name
                param_key = f"params_{template_base_name}"
                if param_key not in st.session_state:
                    st.session_state[param_key] = {}
                param_values = st.session_state[param_key]
                st.session_state["current_template_param_key"] = param_key

                # Sort: _id params come last, after their source params
                def param_sort_key(item):
                    name = item[0]
                    if name.endswith("_id"):
                        return (1, name)  # _id params last
                    return (0, name)

                sorted_params = sorted(parameters.items(), key=param_sort_key)

                # Find first non-id param for fallback auto-generation
                first_source_param = next((p for p, _ in sorted_params if not p.endswith("_id")), None)

                for pname, pinfo in sorted_params:
                    desc = pinfo.get("description", "")
                    example = pinfo.get("example", "")
                    widget_key = f"tmpl_param_{selected_name}_{pname}"

                    # Auto-generate _id params from their base param or first param
                    if pname.endswith("_id"):
                        base_param = pname[:-3]  # e.g., "topic_id" -> "topic"
                        source_param = base_param if base_param in parameters else first_source_param

                        if source_param:
                            source_widget_key = f"tmpl_param_{selected_name}_{source_param}"
                            source_val = st.session_state.get(source_widget_key, "")
                            prev_key = f"prev_{source_param}_{selected_name}"
                            prev_source_val = st.session_state.get(prev_key, "")

                            # Auto-update widget if source changed
                            if source_val != prev_source_val:
                                new_id = to_snake_case(source_val) if source_val else ""
                                st.session_state[widget_key] = new_id
                                st.session_state[prev_key] = source_val

                            param_values[pname] = st.text_input(
                                pname,
                                help=f"Auto-generated from {source_param} (editable)",
                                key=widget_key,
                            )
                        else:
                            param_values[pname] = st.text_input(
                                pname,
                                help=desc,
                                placeholder=f"e.g., {example}" if example else "",
                                key=widget_key,
                            )
                    else:
                        param_values[pname] = st.text_input(
                            pname,
                            help=desc,
                            placeholder=f"e.g., {example}" if example else "",
                            key=widget_key,
                        )

                errors = template_service.validate_parameters(template_data, param_values)

                if errors:
                    st.warning("Please fill in all parameters")
                else:
                    result = template_service.substitute_parameters(template_data, param_values)
                    # Use template name + Topic_Id (or first _id param) as task name
                    id_param = next((p for p in parameters if p.endswith("_id")), None)
                    if id_param and param_values.get(id_param):
                        selected_name = f"{selected_name}_{to_title_case(param_values[id_param])}"
                    else:
                        selected_name = f"{selected_name}_{to_title_case(param_values.get(list(parameters.keys())[0], 'task'))}"
            else:
                result = template_data.copy()
                if "template" in result:
                    del result["template"]

with source_tab2:
    # Load from existing saved tasks
    task_files = list(SAVED_TASKS_DIR.glob("*.json")) if SAVED_TASKS_DIR.exists() else []

    if not task_files:
        st.info("No saved tasks yet. Create tasks from templates first.")
    else:
        task_names = [f.stem for f in sorted(task_files)]
        selected_task = st.selectbox(
            "🔍 Select Existing Task",
            options=task_names,
            index=None,
            placeholder="Search or select a task...",
            key="load_existing_task",
        )

        if selected_task:
            task_path = SAVED_TASKS_DIR / f"{selected_task}.json"
            try:
                with open(task_path) as f:
                    result = json.load(f)
                selected_name = selected_task
                st.success(f"Loaded `{selected_task}`")
            except Exception as e:
                st.error(f"Error loading task: {e}")

# Store result in session state for editing
if result:
    # For template-based loading, track param values to detect changes
    param_key = st.session_state.get("current_template_param_key")
    current_params = st.session_state.get(param_key, {}) if param_key else {}
    params_hash = hash(frozenset(current_params.items())) if current_params else None
    prev_params_hash = st.session_state.get("working_task_params_hash")

    # Update if: new task, name changed, or params changed
    should_update = (
        "working_task" not in st.session_state
        or st.session_state.get("working_task_name") != selected_name
        or (params_hash is not None and params_hash != prev_params_hash)
    )

    if should_update:
        st.session_state["working_task"] = result
        st.session_state["working_task_name"] = selected_name
        st.session_state["working_task_params_hash"] = params_hash
    result = st.session_state["working_task"]

# Display task if we have a result
if result and selected_name:
    actions = result.get("actions", [])

    # Generate JSON from current state (with canonical key order)
    json_str = json.dumps(prepare_for_save(result), indent=2, ensure_ascii=False)

    # Save Task section
    st.markdown("---")
    st.subheader("Save Task")
    task_name = st.text_input("Task Name", value=selected_name, key="task_name_main")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save to Scenario Builder", type="primary", use_container_width=True):
            SAVED_TASKS_DIR.mkdir(parents=True, exist_ok=True)
            save_path = SAVED_TASKS_DIR / f"{task_name}.json"
            with open(save_path, "w") as f:
                f.write(json_str)
            st.success(f"Saved as `{task_name}.json`!")
    with col2:
        st.download_button(
            "📥 Download JSON",
            data=json_str,
            file_name=f"{task_name}.json",
            mime="application/json",
            use_container_width=True,
        )

    # Preview & Edit Task section
    st.markdown("---")
    st.subheader("Preview & Edit Task")

    tab1, tab2 = st.tabs(["📊 Timeline", "📄 JSON"])

    with tab1:
        if actions:
            st.markdown("#### Action Flow")
            render_action_flow(actions)
        else:
            st.info("No actions in this task")

    with tab2:
        st.code(json_str, language="json")

# Sidebar guide
with st.sidebar:
    st.markdown("### How to use")
    st.markdown("""
    **From Template:**
    1. Select a template from dropdown
    2. Configure task parameters
    3. Click an action to edit timeout/instructions
    4. Optionally use **Insert Before/After** to add blocks
    5. Save to use in Scenario Builder

    **Load Existing:**
    1. Switch to "Load Existing Task" tab
    2. Select a previously saved task
    3. Edit in the Preview & Edit panel
    4. Re-save with changes
    """)

    st.markdown("---")
    st.markdown("### Action Types")
    st.markdown("""
    - 💬 **CONVERSATE** — Dialogue with goals
    - 👁️ **GAZE** — Look at participants
    - 🖥️ **SHARE** — Show content on screen
    - 📥 **REQUEST** — Ask for user input
    """)
