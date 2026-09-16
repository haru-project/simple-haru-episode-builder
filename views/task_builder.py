"""
Task Builder - Create individual tasks from templates
"""

import json
import re
import streamlit as st
from pathlib import Path

from src.services.template_service import TemplateService
from src.utils.constants import DEFAULT_TEMPLATE_PATH, ACTION_TYPES, GAZE_MODES, SHARE_MODES, SHARE_TYPES, SHARE_SUBTYPES, IMAGE_SUBTYPES, REQUEST_TYPES

# Saved tasks directory
SAVED_TASKS_DIR = Path(__file__).parent.parent / "data" / "tasks" / "saved"

# ---------------------------------------------------------------------------
# Block templates — extensible: add entries here for new block types
# ---------------------------------------------------------------------------
VOICE_GENRES = ["default", "question", "highnrg", "sad", "serious", "whiny"]

def _build_goal(
    goal_id,
    goal_description,
    timeout_minutes=0,
    timeout_seconds=0,
    max_turns=0,
    criteria=None,
    instructions=None,
    expand_ids=None,
    disable_summarize=False,
):
    """Build a goal JSON string from field values.

    Args:
        expand_ids: Optional list of criterion IDs that should be expanded.
        disable_summarize: Whether summarization is disabled for the whole goal.
    """
    goal = {
        "id": goal_id,
        "description": goal_description,
        "success_criteria": criteria or [],
        "timeout": {},
        "additional_instructions": instructions or [],
        "criteria_expand": [],
        "disable_summarize": bool(disable_summarize),
    }
    mins = int(timeout_minutes)
    secs = int(timeout_seconds)
    turns = int(max_turns)
    if mins > 0 or secs > 0:
        goal["timeout"]["max_time"] = {"minutes": mins, "seconds": secs}
    if turns > 0:
        goal["timeout"]["max_turns"] = turns

    # Add criteria expansion configuration if provided
    if expand_ids:
        for cid in expand_ids:
            # Empty mappings; UI can be extended later to specify source/target
            goal["criteria_expand"].append({"ids": [cid], "mappings": []})

    return json.dumps(goal, ensure_ascii=False)


BLOCK_TEMPLATES = {
    "Conversate": {
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
                    "metainfo": vals["metainfo"] if vals.get("metainfo") else "Conversate",
                }
            ],
        },
    },
    "Converse & Gaze": {
        "action_type": "HARU_CONVERSATE",
        "multi": True,
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
        "companion_fields": [
            {"name": "gaze_type", "label": "Gaze Type", "type": "select", "default": "GROUP",
             "options": ["GROUP", "GAZE_INDIVIDUAL"],
             "help": "GROUP: scan the group. GAZE_INDIVIDUAL: track a specific person."},
            {"name": "gaze_haru_id", "label": "Haru ID", "type": "text", "default": "haru-jp",
             "help": "Robot identifier (for GAZE_INDIVIDUAL).", "content_only": True},
            {"name": "gaze_local_id", "label": "Local ID", "type": "number", "default": 1,
             "help": "Target user ID (for GAZE_INDIVIDUAL).", "content_only": True},
        ],
        "build": lambda vals: [
            {
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
                        "metainfo": vals["metainfo"] if vals.get("metainfo") else "Converse & Gaze",
                    }
                ],
            },
            {
                "action_type": "HARU_GAZE",
                "_bond": True,
                "action_arguments": {
                    "gaze_arguments": {
                        "gaze_mode": "GROUP" if vals["gaze_type"] == "GROUP" else "TRACK_PERSON",
                    }
                },
                "action_content": [{}] if vals["gaze_type"] == "GROUP" else [
                    {
                        "user_id": {
                            "haru_id": vals.get("gaze_haru_id") or "haru-jp",
                            "local_id": int(vals.get("gaze_local_id", 1)),
                        },
                        "value_type": "GAZE_INDIVIDUAL",
                    }
                ],
            },
        ],
    },
    "Request iPads": {
        "action_type": "HARU_REQUEST",
        "fields": [
            {"name": "request_type", "label": "Request Type", "type": "select", "default": "IMAGE_AVATAR",
             "options": REQUEST_TYPES, "help": "Type of content to request from users."},
            {"name": "results_key", "label": "Results Key", "type": "text", "required": True,
             "help": "Key to store results (e.g., local_avatars_results). Can be referenced in later SHARE actions."},
            {"name": "metainfo", "label": "Metainfo", "type": "text", "default": "",
             "help": "Description of the request."},
            {"name": "haru_id", "label": "Haru ID", "type": "text", "default": "haru-jp",
             "help": "Robot identifier."},
            {"name": "local_id", "label": "Local ID", "type": "number", "default": -1,
             "help": "Target user ID (-1 for all users)."},
        ],
        "build": lambda vals: {
            "action_type": "HARU_REQUEST",
            "action_content": [
                {
                    "user_id": {
                        "haru_id": vals["haru_id"] if vals.get("haru_id") else "haru-jp",
                        "local_id": int(vals["local_id"]),
                    },
                    "metainfo": vals["metainfo"] if vals.get("metainfo") else f"Request {vals['request_type']}",
                }
            ],
            "action_arguments": {
                "request_arguments": {
                    "request_type": vals["request_type"],
                }
            },
            "action_results_key": vals["results_key"],
        },
    },
    "Share Video": {
        "action_type": "HARU_SHARE",
        "fields": [
            {"name": "url", "label": "Video URL/Path", "type": "text", "required": True,
             "help": "Path or URL to the video file (e.g., /shared/projector/resources/video.webm)."},
            {"name": "metainfo", "label": "Metainfo", "type": "text", "default": "",
             "help": "Description of the video content."},
            {"name": "share_mode", "label": "Share Mode", "type": "select", "default": "SHOW_SIMPLE",
             "options": SHARE_MODES, "help": "SHOW_SIMPLE: single item. SHOW_ALL: grid."},
            {"name": "video_loop", "label": "Loop", "type": "select", "default": "No",
             "options": ["No", "Yes"], "help": "Loop the video."},
            {"name": "video_mute", "label": "Mute", "type": "select", "default": "No",
             "options": ["No", "Yes"], "help": "Mute the video."},
            {"name": "video_wait", "label": "Wait for Completion", "type": "select", "default": "No",
             "options": ["No", "Yes"], "help": "Wait for video to finish before proceeding."},
        ],
        "build": lambda vals: {
            "action_type": "HARU_SHARE",
            "action_content": [
                {
                    "value": vals["url"],
                    "value_type": "URL_VIDEO",
                    "metainfo": vals["metainfo"] if vals.get("metainfo") else "Video",
                }
            ],
            "action_arguments": {
                "share_arguments": {
                    "share_mode": vals["share_mode"],
                    "share_type": "VIDEO",
                    "share_screen": 1,
                    "share_subtype": "APP_CONTENT",
                    "share_video_args": {
                        "video_loop": vals["video_loop"] == "Yes",
                        "video_mute": vals["video_mute"] == "Yes",
                        "video_wait_completion": vals["video_wait"] == "Yes",
                    },
                }
            },
        },
    },
    "Share Image": {
        "action_type": "HARU_SHARE",
        "fields": [
            {"name": "url", "label": "Image URL/Path", "type": "text", "required": True,
             "help": "Path or URL to the image file (e.g., /shared/projector/resources/image.png)."},
            {"name": "metainfo", "label": "Metainfo", "type": "text", "default": "",
             "help": "Description of the image content."},
            {"name": "share_mode", "label": "Share Mode", "type": "select", "default": "SHOW_SIMPLE",
             "options": SHARE_MODES, "help": "SHOW_SIMPLE: single item. SHOW_ALL: grid."},
            {"name": "share_subtype", "label": "Content Subtype", "type": "select", "default": "APP_CONTENT",
             "options": SHARE_SUBTYPES, "help": "APP_CONTENT: built-in. SHARED_CONTENT: user-shared."},
            {"name": "image_subtype", "label": "Image Subtype", "type": "select", "default": "",
             "options": IMAGE_SUBTYPES, "help": "PHOTO, AVATAR, or DRAWING."},
        ],
        "build": lambda vals: {
            "action_type": "HARU_SHARE",
            "action_content": [
                {
                    "value": vals["url"],
                    "value_type": "URL_IMAGE",
                    "metainfo": vals["metainfo"] if vals.get("metainfo") else "Image",
                }
            ],
            "action_arguments": {
                "share_arguments": {
                    "share_mode": vals["share_mode"],
                    "share_type": "IMAGE",
                    "share_screen": 1,
                    "share_subtype": vals["share_subtype"],
                    **({"share_image_subtype": vals["image_subtype"]} if vals.get("image_subtype") else {}),
                }
            },
        },
    },
    "Share Results": {
        "action_type": "HARU_SHARE",
        "fields": [
            {"name": "results_key", "label": "Results Key", "type": "text", "required": True,
             "help": "Template variable referencing REQUEST results (e.g., local_avatars_results)."},
            {"name": "share_mode", "label": "Share Mode", "type": "select", "default": "SHOW_ALL",
             "options": SHARE_MODES, "help": "SHOW_SIMPLE: single item. SHOW_ALL: grid."},
            {"name": "share_subtype", "label": "Content Subtype", "type": "select", "default": "SHARED_CONTENT",
             "options": SHARE_SUBTYPES, "help": "APP_CONTENT: built-in. SHARED_CONTENT: user-shared."},
            {"name": "image_subtype", "label": "Image Subtype", "type": "select", "default": "AVATAR",
             "options": IMAGE_SUBTYPES[1:], "help": "PHOTO, AVATAR, or DRAWING."},
        ],
        "build": lambda vals: {
            "action_type": "HARU_SHARE",
            "action_content": "{{" + vals["results_key"] + "}}",
            "action_arguments": {
                "share_arguments": {
                    "share_mode": vals["share_mode"],
                    "share_type": "IMAGE",
                    "share_screen": 1,
                    "share_subtype": vals["share_subtype"],
                    "share_image_subtype": vals["image_subtype"],
                }
            },
        },
    },
}


ACTION_KEY_ORDER = [
    "action_id", "wait_for_action_ids", "bond_action_ids",
    "action_type", "action_arguments", "action_goal", "action_content",
    "action_results_key",
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



def to_title_case(text: str) -> str:
    """Convert text to Title_Case with underscores."""
    words = re.split(r"[\s_]+", text.strip())
    return "_".join(word.capitalize() for word in words if word)


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

    # Find parallel groups and merge overlapping ones
    raw_groups = []
    for action in actions:
        aid = action.get("action_id", 0)
        bond_ids = action.get("bond_action_ids", [])
        if bond_ids:
            raw_groups.append({aid} | set(bond_ids))

    # Merge overlapping groups (e.g., {1,2} and {1,3} become {1,2,3})
    merged = True
    while merged:
        merged = False
        new_groups = []
        for group in raw_groups:
            placed = False
            for i, existing in enumerate(new_groups):
                if group & existing:
                    new_groups[i] = existing | group
                    merged = True
                    placed = True
                    break
            if not placed:
                new_groups.append(group)
        raw_groups = new_groups

    parallel_groups = {tuple(sorted(g)): g for g in raw_groups}

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

            compatible = BLOCK_TEMPLATES
            if not compatible:
                st.info("No block templates available.")
            else:
                block_type = st.selectbox(
                    "Block Type",
                    options=list(compatible.keys()),
                    key=f"block_type_{aid}",
                )
                tmpl = compatible[block_type]

                # --- Explicit Content vs Goal choice ---
                mode = st.radio(
                    "Action mode",
                    options=["📄 Content", "🎯 Goal"],
                    horizontal=True,
                    key=f"action_mode_{aid}",
                )
                use_goal = mode == "🎯 Goal"

                field_values = {}
                goal_values = {}

                if not use_goal:
                    # --- Content fields ---
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
                    can_confirm = all(
                        field_values.get(f["name"])
                        for f in tmpl["fields"]
                        if f.get("required")
                    )

                if not use_goal:
                    pass  # can_confirm already set above
                else:
                    # --- Goal fields ---
                    goal_values["goal_id"] = st.text_input(
                        "Goal ID", key=f"goal_id_{aid}",
                        help="Unique identifier (e.g., greet, discuss_topic).",
                    )
                    goal_values["goal_desc"] = st.text_area(
                        "Goal Description", key=f"goal_desc_{aid}",
                        help="What the agent should achieve.",
                    )

                    # Timeout
                    st.markdown("##### Timeout")
                    gcol1, gcol2, gcol3 = st.columns(3)
                    with gcol1:
                        goal_values["timeout_mins"] = st.number_input(
                            "Minutes", min_value=0, value=3, key=f"goal_mins_{aid}")
                    with gcol2:
                        goal_values["timeout_secs"] = st.number_input(
                            "Seconds", min_value=0, max_value=59, value=0, key=f"goal_secs_{aid}")
                    with gcol3:
                        goal_values["max_turns"] = st.number_input(
                            "Max Turns", min_value=0, value=0, key=f"goal_turns_{aid}",
                            help="0 = no limit.")

                    goal_values["disable_summarize"] = st.toggle(
                        "Disable Summarize", value=False, key=f"goal_disable_summarize_{aid}",
                        help="Applies to the entire goal: when on, the conversation history from this goal is not summarized.",
                    )

                    # Success criteria
                    st.markdown("##### Success Criteria")
                    criteria_key = f"goal_criteria_{aid}"
                    if criteria_key not in st.session_state:
                        st.session_state[criteria_key] = []

                    criteria_list = st.session_state[criteria_key]
                    to_remove = None
                    for ci, crit in enumerate(criteria_list):
                        ccol1, ccol2, ccol3 = st.columns([2, 5, 1])
                        with ccol1:
                            criteria_list[ci]["id"] = st.text_input(
                                "ID", value=crit.get("id", f"c{ci+1}"),
                                key=f"crit_id_{aid}_{ci}", label_visibility="collapsed",
                            )
                        with ccol2:
                            criteria_list[ci]["description"] = st.text_input(
                                "Description", value=crit.get("description", ""),
                                key=f"crit_desc_{aid}_{ci}", label_visibility="collapsed",
                            )
                        with ccol3:
                            if st.button("✕", key=f"crit_del_{aid}_{ci}"):
                                to_remove = ci

                        # Criterion timeout
                        crit_timeout = crit.get("timeout", {})
                        crit_max_time = crit_timeout.get("max_time", {})
                        with st.expander(f"⏱️ Timeout for `{crit.get('id', f'c{ci+1}')}`"):
                            tc1, tc2, tc3 = st.columns(3)
                            with tc1:
                                ct_mins = st.number_input(
                                    "Minutes", min_value=0,
                                    value=crit_max_time.get("minutes", 0),
                                    key=f"crit_mins_{aid}_{ci}",
                                )
                            with tc2:
                                ct_secs = st.number_input(
                                    "Seconds", min_value=0, max_value=59,
                                    value=crit_max_time.get("seconds", 0),
                                    key=f"crit_secs_{aid}_{ci}",
                                )
                            with tc3:
                                ct_turns = st.number_input(
                                    "Max Turns", min_value=0,
                                    value=crit_timeout.get("max_turns", 0) or 0,
                                    key=f"crit_turns_{aid}_{ci}",
                                )
                            ct = {}
                            if ct_mins > 0 or ct_secs > 0:
                                ct["max_time"] = {"minutes": ct_mins, "seconds": ct_secs}
                            if ct_turns > 0:
                                ct["max_turns"] = ct_turns
                            criteria_list[ci]["timeout"] = ct

                    if to_remove is not None:
                        criteria_list.pop(to_remove)
                        st.rerun()
                    if st.button("+ Add Criterion", key=f"add_crit_{aid}"):
                        criteria_list.append({
                            "id": f"c{len(criteria_list)+1}",
                            "description": "",
                            "timeout": {},
                            "expand": False,
                        })
                        st.rerun()

                    # Additional instructions
                    st.markdown("##### Additional Instructions")
                    instr_key = f"goal_instructions_{aid}"
                    if instr_key not in st.session_state:
                        st.session_state[instr_key] = []

                    instr_list = st.session_state[instr_key]
                    instr_to_remove = None
                    for ii, instr in enumerate(instr_list):
                        icol1, icol2 = st.columns([6, 1])
                        with icol1:
                            instr_list[ii] = st.text_input(
                                "Instruction", value=instr,
                                key=f"instr_{aid}_{ii}", label_visibility="collapsed",
                            )
                        with icol2:
                            if st.button("✕", key=f"instr_del_{aid}_{ii}"):
                                instr_to_remove = ii
                    if instr_to_remove is not None:
                        instr_list.pop(instr_to_remove)
                        st.rerun()
                    if st.button("+ Add Instruction", key=f"add_instr_goal_{aid}"):
                        instr_list.append("")
                        st.rerun()

                    can_confirm = bool(goal_values.get("goal_id") and goal_values.get("goal_desc"))

                # --- Companion fields (always shown after content/goal, e.g. gaze settings) ---
                companion_values = {}
                companion_fields = tmpl.get("companion_fields", [])
                if companion_fields:
                    st.markdown("---")
                    for field in companion_fields:
                        if field.get("content_only") and use_goal:
                            continue
                        fkey = f"companion_{aid}_{field['name']}"
                        help_text = field.get("help")
                        if field["type"] == "text_area":
                            companion_values[field["name"]] = st.text_area(
                                field["label"], key=fkey, help=help_text,
                            )
                        elif field["type"] == "number":
                            companion_values[field["name"]] = st.number_input(
                                field["label"], value=field.get("default", 0), key=fkey, help=help_text,
                            )
                        elif field["type"] == "select":
                            options = field.get("options", [])
                            default_idx = options.index(field["default"]) if field.get("default") in options else 0
                            companion_values[field["name"]] = st.selectbox(
                                field["label"], options=options, index=default_idx, key=fkey, help=help_text,
                            )
                        else:
                            companion_values[field["name"]] = st.text_input(
                                field["label"], value=field.get("default", ""), key=fkey, help=help_text,
                            )

                form_cols = st.columns(2)
                with form_cols[0]:
                    if st.button(
                        "✅ Confirm", key=f"confirm_insert_{aid}",
                        disabled=not can_confirm, use_container_width=True,
                    ):
                        task = st.session_state.get("working_task")
                        if task:
                            if use_goal:
                                criteria = []
                                for c in st.session_state.get(f"goal_criteria_{aid}", []):
                                    if c.get("id") and c.get("description"):
                                        crit_entry = {"id": c["id"], "description": c["description"]}
                                        if c.get("timeout"):
                                            crit_entry["timeout"] = c["timeout"]
                                        criteria.append(crit_entry)
                                instructions = [
                                    i for i in st.session_state.get(f"goal_instructions_{aid}", [])
                                    if i.strip()
                                ]
                                goal_str = _build_goal(
                                    goal_values["goal_id"], goal_values["goal_desc"],
                                    goal_values["timeout_mins"], goal_values["timeout_secs"],
                                    goal_values["max_turns"], criteria, instructions,
                                    disable_summarize=goal_values.get("disable_summarize", False),
                                )
                                # For multi-action templates, build with companion values and add goal to first
                                if tmpl.get("multi"):
                                    build_vals = {**field_values, **companion_values}
                                    action_list = tmpl["build"](build_vals)
                                    action_list[0]["action_goal"] = goal_str
                                    action_list[0]["action_content"] = []
                                else:
                                    action_list = [{
                                        "action_type": tmpl["action_type"],
                                        "action_goal": goal_str,
                                        "action_content": [],
                                    }]
                            else:
                                build_vals = {**field_values, **companion_values}
                                result = tmpl["build"](build_vals)
                                action_list = result if isinstance(result, list) else [result]

                            # Insert actions — handle multi-action blocks with bonding
                            first_action = action_list[0]
                            insert_action(task, aid, position, first_action)
                            if len(action_list) > 1:
                                # Find the inserted action's new ID
                                actions = task.get("actions", [])
                                first_new = next(
                                    a for a in actions
                                    if a.get("action_type") == first_action.get("action_type")
                                    and a.get("action_goal") == first_action.get("action_goal")
                                    and a.get("action_content") == first_action.get("action_content")
                                )
                                first_id = first_new["action_id"]
                                for extra in action_list[1:]:
                                    if extra.pop("_bond", False):
                                        extra["bond_action_ids"] = [first_id]
                                    insert_action(task, first_id, "after", extra)

                            st.session_state.pop("insert_mode", None)
                            st.session_state.pop(f"goal_criteria_{aid}", None)
                            st.session_state.pop(f"goal_instructions_{aid}", None)
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

            # Render routine editor (if applicable)
            _render_routine_editor(action, aid, selected_name)

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


def _render_routine_editor(action: dict, aid: int, task_name: str) -> None:
    """Render UI for editing *both* routine numbers and TTS of a CONVERSATE action.

    The editor is displayed only when the action's ``action_content`` contains a
    ``value`` list with at least one entry that has a ``tts`` field (the value may
    be an empty string). It allows the user to:

    * Edit the TTS text for each turn.
    * Edit the routine number for each turn.
    * Add a new turn (empty TTS, routine 0).
    * Remove an existing turn.

    All changes are written back to the ``action`` dict and the global
    ``working_task`` state so they persist when the task is saved.
    """
    # Extract the list of turns from the first content block
    content = action.get("action_content", [])
    if not (content and isinstance(content, list)):
        return
    value_list = content[0].get("value", [])
    if not (value_list and isinstance(value_list, list)):
        return

    # Only show the editor if at least one entry has a ``tts`` key (value may be empty)
    if not any("tts" in v for v in value_list):
        return

    st.markdown("#### 🎵 Routine & TTS Editor")
    # Session state key that holds a mutable list of turn dicts
    ss_key = f"routine_tts_edit_{aid}_{task_name}"
    if ss_key not in st.session_state:
        # Initialise with a deep copy of the current values (avoid mutating original)
        st.session_state[ss_key] = [
            {"tts": v.get("tts", ""), "routine": v.get("routine", 2001)} for v in value_list
        ]

    turn_data = st.session_state[ss_key]

    # Load routine catalogue (once per session) for dropdown options
    routine_cache_key = "routine_catalogue"
    if routine_cache_key not in st.session_state:
        routines_path = Path(__file__).parent.parent / "data" / "routines" / "routines_haru2.json"
        try:
            with open(routines_path) as f:
                catalogue = json.load(f)
        except Exception as e:
            st.error(f"Failed to load routines catalogue: {e}")
            catalogue = {}
        # Build mapping id -> name and list of "Name (ID)" options
        id_to_name = {int(k): v.get("name", "") for k, v in catalogue.items()}
        options = [f"{name} ({rid})" for rid, name in sorted(id_to_name.items())]
        st.session_state[routine_cache_key] = {
            "catalogue": catalogue,
            "id_to_name": id_to_name,
            "options": options,
        }

    routine_data = st.session_state[routine_cache_key]
    options = routine_data["options"]
    # Helper to map display string back to numeric id
    option_to_id = {opt: int(opt.split("(")[-1].rstrip(")")) for opt in options}

    # Render UI for each turn
    to_delete = None
    for idx, turn in enumerate(turn_data):
        col_tts, col_routine, col_del = st.columns([5, 2, 1])
        with col_tts:
            # Show a visible label for each TTS input so users can identify the field
            turn["tts"] = st.text_area(
                f"TTS {idx + 1}",
                value=turn.get("tts", ""),
                key=f"tts_edit_{aid}_{task_name}_{idx}",
                height=80,
            )
        with col_routine:
            # Determine current routine id and its index in the options list
            current_id = turn.get("routine", 0)
            default_index = 0
            for i, opt in enumerate(options):
                if option_to_id[opt] == current_id:
                    default_index = i
                    break
            selected_opt = st.selectbox(
                f"Routine {idx + 1}",
                options=options,
                index=default_index,
                key=f"routine_sel_{aid}_{task_name}_{idx}",
            )
            turn["routine"] = option_to_id.get(selected_opt, 0)
        with col_del:
            if st.button("🗑️", key=f"del_turn_{aid}_{task_name}_{idx}"):
                to_delete = idx

        st.markdown("---")

    if to_delete is not None:
        turn_data.pop(to_delete)
        st.rerun()

    # Button to add a new empty turn
    if st.button("➕ Add Turn", key=f"add_turn_{aid}_{task_name}"):
        turn_data.append({"tts": "", "routine": 0})
        st.rerun()

    # Persist changes back to the action if anything changed
    # Compare with original list of dicts
    original = [{"tts": v.get("tts", ""), "routine": v.get("routine", 0)} for v in value_list]
    if turn_data != original:
        # Update the underlying content structure – keep any other keys in the block
        content[0]["value"] = turn_data
        action["action_content"] = content
        # Update the global working task actions list
        if "working_task" in st.session_state:
            st.session_state["working_task"]["actions"] = [
                a if a.get("action_id") != aid else action
                for a in st.session_state["working_task"].get("actions", [])
            ]

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

    # Initialize session state for editing the goal description
    if "editing_goal_description" not in st.session_state:
        st.session_state.editing_goal_description = False

    # Show either normal view or edit form
    if not st.session_state.editing_goal_description:

        # Display goal description
        st.markdown(f"**{goal.get('description', 'Goal')}**")

        # Edit button
        if st.button("Edit Goal Description"):
            st.session_state.editing_goal_description = True
            st.rerun()

    else:
        # Edit form
        with st.form("edit_goal_description_form"):

            new_desc = st.text_area(
                "Edit Goal Description",
                value=goal.get("description", "")
            )

            save = st.form_submit_button("Save")
            cancel = st.form_submit_button("Cancel")

            if save:
                goal["description"] = new_desc
                if action is not None:
                    action["action_goal"] = json.dumps(goal, ensure_ascii=False)

                st.session_state.editing_goal_description = False
                st.rerun()

            if cancel:
                st.session_state.editing_goal_description = False
                st.rerun()

    criteria = goal.get("success_criteria", [])
    criteria_expand = goal.get("criteria_expand", [])

    # Criteria Session State
    if "editing_criterion" not in st.session_state:
        st.session_state.editing_criterion = None

    if "adding_criterion" not in st.session_state:
        st.session_state.adding_criterion = False

    if "deleting_criterion" not in st.session_state:
        st.session_state.deleting_criterion = None

    expanded_ids = {cid for exp in criteria_expand for cid in exp.get("ids", [])}

    st.markdown("### Success Criteria")

    # ADD BUTTON
    if not st.session_state.adding_criterion:
        if st.button("➕ Add Criterion"):
            st.session_state.adding_criterion = True
            st.rerun()

    # ADD FORM
    if st.session_state.adding_criterion:
        with st.form("add_criterion_form"):
            new_id = st.text_input(
                "Criterion ID",
                value=f"C{len(criteria)+1}"
            )
            new_desc = st.text_input("Description")
            save = st.form_submit_button("Add")
            cancel = st.form_submit_button("Cancel")

            if save:
                if any(c["id"] == new_id for c in criteria):
                    st.error("Criterion ID already exists.")
                else:
                    new_criterion = {
                        "id": new_id,
                        "description": new_desc,
                        "timeout": {}
                    }
                    criteria.append(new_criterion)
                    if action is not None:
                        action["action_goal"] = json.dumps(goal, ensure_ascii=False)
                    st.session_state.adding_criterion = False
                    st.rerun()
            if cancel:
                st.session_state.adding_criterion = False
                st.rerun()

    # CRITERIA LIST
    for i, c in enumerate(criteria):

        cid = c.get("id", "")
        desc = c.get("description", "")
        criteria_timeout = c.get("timeout", {})

        expand_marker = " 🔄" if cid in expanded_ids else ""

        col1, col2, col3 = st.columns([6, 1, 1])

        # NORMAL VIEW
        if st.session_state.editing_criterion != cid:
            with col1:
                st.markdown(f"- `{cid}`{expand_marker}: {desc}")
            with col2:
                if st.button("Edit", key=f"edit_{cid}"):
                    st.session_state.editing_criterion = cid
                    st.rerun()
            with col3:
                if st.button("🗑", key=f"delete_{cid}"):
                    st.session_state.deleting_criterion = cid
                    st.rerun()
        # EDIT MODE
        else:
            with st.form(f"edit_form_{cid}"):
                new_desc = st.text_input(
                    f"Edit description for {cid}",
                    value=desc
                )
                save = st.form_submit_button("Save")
                cancel = st.form_submit_button("Cancel")
                if save:
                    criteria[i]["description"] = new_desc
                    if action is not None:
                        action["action_goal"] = json.dumps(goal, ensure_ascii=False)
                    st.session_state.editing_criterion = None
                    st.rerun()
                if cancel:
                    st.session_state.editing_criterion = None
                    st.rerun()

        # DELETE CONFIRM
        if st.session_state.deleting_criterion == cid:
            st.warning(f"Delete criterion `{cid}`?")
            colA, colB = st.columns(2)
            with colA:
                if st.button("Confirm Delete", key=f"confirm_delete_{cid}"):
                    criteria.pop(i)
                    if action is not None:
                        action["action_goal"] = json.dumps(goal, ensure_ascii=False)
                    st.session_state.deleting_criterion = None
                    st.rerun()
            with colB:
                if st.button("Cancel", key=f"cancel_delete_{cid}"):
                    st.session_state.deleting_criterion = None
                    st.rerun()

        # Crtieria Timeout
        timeout_block(
            action,
            goal,
            criteria_timeout,
            c,
            id=cid,
            title=f"Timeout for Criterion `{cid}`"
        )

    # GOAL Timeout
    timeout = goal.get("timeout", {})

    timeout_block(
        action,
        goal,
        timeout,
        goal,
        action_id,
        title="Goal Timeout"
    )

    # Goal-level summarization toggle (applies to the whole goal, not per criterion)
    summarize_key = f"disable_summarize_{task_name}_{action_id}"
    if summarize_key not in st.session_state:
        st.session_state[summarize_key] = bool(goal.get("disable_summarize", False))

    def update_disable_summarize():
        goal["disable_summarize"] = bool(st.session_state[summarize_key])
        if action is not None:
            action["action_goal"] = json.dumps(goal, ensure_ascii=False)

    st.toggle(
        "Disable Summarize",
        key=summarize_key,
        on_change=update_disable_summarize,
        help="When enabled, the conversation history for this entire goal will not be summarized.",
    )

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

                for pname, pinfo in parameters.items():
                    desc = pinfo.get("description", "")
                    example = pinfo.get("example", "")
                    widget_key = f"tmpl_param_{selected_name}_{pname}"

                    options = pinfo.get("options")
                    param_type = pinfo.get("type")
                    if options:
                        param_values[pname] = st.selectbox(
                            pname,
                            options=options,
                            help=desc,
                            key=widget_key,
                        )
                    elif param_type == "path":
                        base_path = pinfo.get("base_path", "/")
                        browse_dir = Path(base_path)
                        if browse_dir.is_dir():
                            files = sorted(
                                (f for f in browse_dir.iterdir()
                                if f.is_file() and not f.name.startswith(".")),
                                key=lambda f: f.name,
                            )
                            if files:
                                param_values[pname] = str(st.selectbox(
                                    pname,
                                    options=files,
                                    format_func=lambda f: f.name,
                                    key=widget_key,
                                ))
                            else:
                                st.warning(f"No files found in {browse_dir}")
                                param_values[pname] = ""
                        else:
                            st.warning(f"Directory not found: {browse_dir}")
                            param_values[pname] = ""
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
                    # Build task name from template name + visible parameter values only
                    name_parts = []
                    for pname in parameters:
                        val = param_values.get(pname, "")
                        if not val:
                            continue
                        # For file paths, use only the filename without extension
                        if "/" in val or "\\" in val:
                            val = Path(val).stem
                        name_parts.append(to_title_case(val))
                    if name_parts:
                        selected_name = f"{selected_name}_{'_'.join(name_parts)}"
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
        st.session_state["task_name_main"] = selected_name
    result = st.session_state["working_task"]

# Display task if we have a result
if result and selected_name:
    actions = result.get("actions", [])

    # Generate JSON from current state (with canonical key order)
    json_str = json.dumps(prepare_for_save(result), indent=2, ensure_ascii=False)

    # Save Task section
    st.markdown("---")
    st.subheader("Save Task")
    if "task_name_main" not in st.session_state:
        st.session_state["task_name_main"] = selected_name
    task_name = st.text_input("Task Name", key="task_name_main")
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
