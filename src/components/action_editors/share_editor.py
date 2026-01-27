"""Editor for HARU_SHARE actions."""

import streamlit as st
from ..content_editor import render_content_editor
from ...utils.constants import SHARE_MODES, SHARE_TYPES, SHARE_SUBTYPES


def render_share_editor(editing_action: dict | None = None) -> dict:
    """
    Render HARU_SHARE specific fields.

    Returns dict with share-specific field values.
    """
    st.markdown("---")
    st.markdown("### HARU_SHARE Configuration")

    # Get defaults from editing action
    default_share_mode = "SHOW_SIMPLE"
    default_share_type = "VIDEO"
    default_share_screen = 1
    default_share_subtype = "APP_CONTENT"
    default_video_loop = False
    default_video_mute = False
    default_video_wait = False
    default_image_subtype = ""
    default_content = []

    if editing_action and editing_action.get("action_type") == "HARU_SHARE":
        args = editing_action.get("action_arguments", {})
        share_args = args.get("share_arguments", {})
        default_share_mode = share_args.get("share_mode", default_share_mode)
        default_share_type = share_args.get("share_type", default_share_type)
        default_share_screen = share_args.get("share_screen", default_share_screen)
        default_share_subtype = share_args.get("share_subtype", default_share_subtype)
        video_args = share_args.get("share_video_args", {})
        default_video_loop = video_args.get("video_loop", default_video_loop)
        default_video_mute = video_args.get("video_mute", default_video_mute)
        default_video_wait = video_args.get("video_wait_completion", default_video_wait)
        default_image_subtype = share_args.get("share_image_subtype", "")
        default_content = editing_action.get("action_content", [])

    # Share arguments
    col1, col2 = st.columns(2)

    with col1:
        share_mode = st.selectbox(
            "Share Mode",
            options=SHARE_MODES,
            index=SHARE_MODES.index(default_share_mode) if default_share_mode in SHARE_MODES else 0,
            key="share_mode",
            help="SHOW_SIMPLE: Display single item. SHOW_ALL: Display all items in grid.",
        )

        share_type = st.selectbox(
            "Share Type",
            options=SHARE_TYPES,
            index=SHARE_TYPES.index(default_share_type) if default_share_type in SHARE_TYPES else 0,
            key="share_type",
        )

    with col2:
        share_screen = st.number_input(
            "Screen",
            min_value=1,
            value=default_share_screen,
            step=1,
            key="share_screen",
            help="Which screen to display content on",
        )

        share_subtype = st.selectbox(
            "Share Subtype",
            options=SHARE_SUBTYPES,
            index=SHARE_SUBTYPES.index(default_share_subtype) if default_share_subtype in SHARE_SUBTYPES else 0,
            key="share_subtype",
            help="APP_CONTENT: Built-in content. SHARED_CONTENT: User-shared content.",
        )

    # Type-specific options
    share_video_args = None
    share_image_subtype = None

    if share_type == "VIDEO":
        st.markdown("#### Video Options")
        col1, col2, col3 = st.columns(3)
        with col1:
            video_loop = st.checkbox("Loop", value=default_video_loop, key="video_loop")
        with col2:
            video_mute = st.checkbox("Mute", value=default_video_mute, key="video_mute")
        with col3:
            video_wait = st.checkbox(
                "Wait for completion",
                value=default_video_wait,
                key="video_wait",
            )
        share_video_args = {
            "video_loop": video_loop,
            "video_mute": video_mute,
            "video_wait_completion": video_wait,
        }

    elif share_type == "IMAGE":
        st.markdown("#### Image Options")
        share_image_subtype = st.text_input(
            "Image Subtype (optional)",
            value=default_image_subtype,
            key="image_subtype",
            help="e.g., IMAGE_AVATAR, IMAGE_PHOTO",
        )

    # Content editor
    st.markdown("#### Share Content")
    action_content = render_content_editor(
        "HARU_SHARE",
        default_content,
        key_prefix="share_content",
    )

    # Build share_arguments
    share_arguments = {
        "share_mode": share_mode,
        "share_type": share_type,
        "share_screen": int(share_screen),
        "share_subtype": share_subtype,
    }

    if share_video_args:
        share_arguments["share_video_args"] = share_video_args

    if share_image_subtype:
        share_arguments["share_image_subtype"] = share_image_subtype

    return {
        "action_arguments": {
            "share_arguments": share_arguments
        },
        "action_content": action_content if action_content else [],
    }


def reset_share_editor_state():
    """Reset share editor session state."""
    keys_to_reset = [k for k in st.session_state.keys() if k.startswith("share_")]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
