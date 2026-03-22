"""Utility helper functions."""

import json
import streamlit as st


def parse_int_list(s: str) -> list[int]:
    """Parse comma-separated integers like '1, 2,3' into [1,2,3]."""
    s = s.strip()
    if not s:
        return []
    try:
        return [int(x.strip()) for x in s.split(",") if x.strip()]
    except ValueError:
        st.warning("Could not parse integer list; please use comma-separated integers.")
        return []


def format_json(data: dict, indent: int = 4) -> str:
    """Format dictionary as pretty JSON string."""
    return json.dumps(data, indent=indent, ensure_ascii=False)


def minify_json(data: dict) -> str:
    """Format dictionary as minified JSON string."""
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def safe_json_loads(s: str) -> dict | None:
    """Safely parse JSON string, return None on error."""
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def get_next_action_id(actions: list) -> int:
    """Get the next available action ID."""
    if not actions:
        return 1
    return max(a.get("action_id", 0) for a in actions) + 1


def substitute_template_params(text: str, params: dict[str, str]) -> str:
    """Substitute {param} placeholders in text with values."""
    result = text
    for key, value in params.items():
        result = result.replace(f"{{{key}}}", value)
    return result
