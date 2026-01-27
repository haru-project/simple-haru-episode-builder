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


def to_snake_case(text: str) -> str:
    """Convert text to snake_case identifier."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


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
            render_goal_visualization(goal, action=action, action_id=aid)

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


def render_goal_visualization(goal_str: str, action: dict = None, action_id: int = 0):
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
    if criteria:
        st.markdown("**Success Criteria:**")
        for c in criteria:
            cid = c.get("id", "")
            desc = c.get("description", "")
            st.markdown(f"- `{cid}`: {desc}")

    # Editable timeout
    timeout = goal.get("timeout", {})
    with st.expander("⏱️ Timeout", expanded=bool(timeout)):
        max_time = timeout.get("max_time", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            mins = st.number_input(
                "Minutes",
                min_value=0,
                value=max_time.get("minutes", 0),
                key=f"timeout_mins_{action_id}",
            )
        with col2:
            secs = st.number_input(
                "Seconds",
                min_value=0,
                max_value=59,
                value=max_time.get("seconds", 0),
                key=f"timeout_secs_{action_id}",
            )
        with col3:
            turns = st.number_input(
                "Max Turns",
                min_value=0,
                value=timeout.get("max_turns", 0) or 0,
                key=f"timeout_turns_{action_id}",
            )

        # Update timeout if changed
        if action is not None:
            new_timeout = {}
            if mins > 0 or secs > 0:
                new_timeout["max_time"] = {"minutes": mins, "seconds": secs}
            if turns > 0:
                new_timeout["max_turns"] = turns
            if new_timeout != timeout:
                goal["timeout"] = new_timeout
                action["action_goal"] = json.dumps(goal, ensure_ascii=False)

    # Editable additional instructions as list
    instructions = goal.get("additional_instructions", [])

    # Initialize session state for instructions list
    instr_key = f"instructions_list_{action_id}"
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
                    key=f"instr_{action_id}_{idx}",
                    label_visibility="collapsed",
                )
                if new_val != instr:
                    current_instructions[idx] = new_val
            with col2:
                if st.button("🗑️", key=f"del_instr_{action_id}_{idx}", help="Delete"):
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
                key=f"new_instr_{action_id}",
                placeholder="Add new instruction...",
                label_visibility="collapsed",
            )
        with col2:
            if st.button("➕", key=f"add_instr_{action_id}", help="Add"):
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

                param_key = f"params_{selected_name}"
                if param_key not in st.session_state:
                    st.session_state[param_key] = {}
                param_values = st.session_state[param_key]

                sorted_params = sorted(parameters.items(), key=lambda x: (x[0] == "topic_id", x[0]))

                for pname, pinfo in sorted_params:
                    desc = pinfo.get("description", "")
                    example = pinfo.get("example", "")

                    if pname == "topic_id" and "topic" in parameters:
                        topic_val = param_values.get("topic", "")
                        current_val = param_values.get(pname, "")
                        if not current_val or current_val == to_snake_case(st.session_state.get(f"prev_topic_{selected_name}", "")):
                            current_val = to_snake_case(topic_val) if topic_val else ""
                        st.session_state[f"prev_topic_{selected_name}"] = topic_val
                        param_values[pname] = st.text_input(
                            pname,
                            value=current_val,
                            help="Auto-generated from topic (editable)",
                            key=f"tmpl_param_{pname}",
                        )
                    else:
                        param_values[pname] = st.text_input(
                            pname,
                            value=param_values.get(pname, ""),
                            help=desc,
                            placeholder=f"e.g., {example}" if example else "",
                            key=f"tmpl_param_{pname}",
                        )

                errors = template_service.validate_parameters(template_data, param_values)

                if errors:
                    st.warning("Please fill in all parameters")
                else:
                    result = template_service.substitute_parameters(template_data, param_values)
                    selected_name = f"{selected_name}_{param_values.get(list(parameters.keys())[0], 'task')}"
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
    if "working_task" not in st.session_state or st.session_state.get("working_task_name") != selected_name:
        st.session_state["working_task"] = result
        st.session_state["working_task_name"] = selected_name
    result = st.session_state["working_task"]

# Display task if we have a result
if result and selected_name:
    actions = result.get("actions", [])

    # Generate JSON from current state
    json_str = json.dumps(result, indent=2, ensure_ascii=False)

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
    4. Save to use in Scenario Builder

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
