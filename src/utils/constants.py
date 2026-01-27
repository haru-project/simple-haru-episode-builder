"""Constants and enums for the Haru Episode Builder."""

from pathlib import Path

# Action types
ACTION_TYPES = [
    "HARU_CONVERSATE",
    "HARU_GAZE",
    "HARU_SHARE",
    "HARU_REQUEST",
]

# Content types organized by action type
CONTENT_TYPES_BY_ACTION = {
    "HARU_CONVERSATE": [
        "JSON_CONVERSATE_MULTITTS",
        "JSON_EXPRESSIVE_TTS_SYNCED_ROUTINES",
    ],
    "HARU_GAZE": [
        "GAZE_INDIVIDUAL",
        "JSON_GAZE_MULTI_INDIVIDUAL",
        "GAZE_STOP",
    ],
    "HARU_SHARE": [
        "TEXT",
        "URL_IMAGE",
        "URL_VIDEO",
    ],
    "HARU_REQUEST": [],  # REQUEST uses user_id targeting, not value_type
}

# Gaze modes
GAZE_MODES = [
    "TRACK_PERSON",
    "GROUP",
]

# Share modes
SHARE_MODES = [
    "SHOW_SIMPLE",
    "SHOW_ALL",
]

# Share types
SHARE_TYPES = [
    "IMAGE",
    "VIDEO",
    "TEXT",
]

# Share subtypes
SHARE_SUBTYPES = [
    "APP_CONTENT",
    "SHARED_CONTENT",
]

# Request types
REQUEST_TYPES = [
    "IMAGE_AVATAR",
    "IMAGE_PHOTO",
    "TEXT",
]

# Default template path (relative to project root)
DEFAULT_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "data" / "tasks" / "templates"

# Common participant variable sources for criteria expansion
PARTICIPANT_SOURCES = [
    "participants_start_right",
    "participants_start_left",
    "participants_all",
    "participants_random",
]
