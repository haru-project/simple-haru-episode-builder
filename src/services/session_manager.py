"""Session state management for the Streamlit app."""

import streamlit as st
from typing import Any


class SessionManager:
    """Manages session state for the episode builder."""

    # Default values for session state
    DEFAULTS = {
        "actions": [],
        "editing_index": None,
        "episode_metadata": {
            "app_id": "test",
            "episode_id": "1",
            "haru_id": "haru-jp",
            "stage_id": 1,
            "task_id": 1,
            "ready": False,
            "mute": True,
            "teleconference_on": True,
            "description": "",
        },
        "template_params": {},
        "loaded_template": None,
        "import_errors": [],
        "import_warnings": [],
    }

    @classmethod
    def initialize(cls) -> None:
        """Initialize all session state variables with defaults."""
        for key, default_value in cls.DEFAULTS.items():
            if key not in st.session_state:
                st.session_state[key] = (
                    default_value.copy()
                    if isinstance(default_value, (list, dict))
                    else default_value
                )

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a session state value."""
        cls.initialize()
        return st.session_state.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a session state value."""
        cls.initialize()
        st.session_state[key] = value

    @classmethod
    def get_actions(cls) -> list[dict]:
        """Get the current actions list."""
        cls.initialize()
        return st.session_state.actions

    @classmethod
    def set_actions(cls, actions: list[dict]) -> None:
        """Set the actions list."""
        cls.initialize()
        st.session_state.actions = actions

    @classmethod
    def add_action(cls, action: dict) -> None:
        """Add an action to the list."""
        cls.initialize()
        st.session_state.actions.append(action)

    @classmethod
    def update_action(cls, index: int, action: dict) -> None:
        """Update an action at the specified index."""
        cls.initialize()
        if 0 <= index < len(st.session_state.actions):
            st.session_state.actions[index] = action

    @classmethod
    def delete_action(cls, index: int) -> None:
        """Delete an action at the specified index."""
        cls.initialize()
        if 0 <= index < len(st.session_state.actions):
            st.session_state.actions.pop(index)

    @classmethod
    def get_editing_index(cls) -> int | None:
        """Get the index of the action being edited."""
        cls.initialize()
        return st.session_state.editing_index

    @classmethod
    def set_editing_index(cls, index: int | None) -> None:
        """Set the editing index."""
        cls.initialize()
        st.session_state.editing_index = index

    @classmethod
    def clear_editing(cls) -> None:
        """Clear the editing state."""
        cls.set_editing_index(None)

    @classmethod
    def get_metadata(cls) -> dict:
        """Get episode metadata."""
        cls.initialize()
        return st.session_state.episode_metadata

    @classmethod
    def update_metadata(cls, **kwargs) -> None:
        """Update episode metadata."""
        cls.initialize()
        st.session_state.episode_metadata.update(kwargs)

    @classmethod
    def get_episode_dict(cls) -> dict:
        """Get the complete episode as a dictionary."""
        cls.initialize()
        metadata = cls.get_metadata()
        return {
            **metadata,
            "actions": cls.get_actions(),
        }

    @classmethod
    def load_episode(cls, episode_dict: dict) -> None:
        """Load an episode from a dictionary."""
        cls.initialize()
        # Extract metadata
        metadata_keys = [
            "app_id",
            "episode_id",
            "haru_id",
            "stage_id",
            "task_id",
            "ready",
            "mute",
            "teleconference_on",
            "description",
        ]
        metadata = {k: episode_dict.get(k, cls.DEFAULTS["episode_metadata"].get(k)) for k in metadata_keys}
        st.session_state.episode_metadata = metadata

        # Load actions
        st.session_state.actions = episode_dict.get("actions", [])

        # Clear editing state
        cls.clear_editing()

    @classmethod
    def reset(cls) -> None:
        """Reset all session state to defaults."""
        for key, default_value in cls.DEFAULTS.items():
            st.session_state[key] = (
                default_value.copy()
                if isinstance(default_value, (list, dict))
                else default_value
            )
