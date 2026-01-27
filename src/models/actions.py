"""Action models for Haru episodes."""

from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Supported action types."""

    HARU_CONVERSATE = "HARU_CONVERSATE"
    HARU_GAZE = "HARU_GAZE"
    HARU_SHARE = "HARU_SHARE"
    HARU_REQUEST = "HARU_REQUEST"


class ContentType(str, Enum):
    """Content value types for actions."""

    # Conversate content types
    JSON_CONVERSATE_MULTITTS = "JSON_CONVERSATE_MULTITTS"
    JSON_EXPRESSIVE_TTS_SYNCED_ROUTINES = "JSON_EXPRESSIVE_TTS_SYNCED_ROUTINES"

    # Gaze content types
    GAZE_INDIVIDUAL = "GAZE_INDIVIDUAL"
    JSON_GAZE_MULTI_INDIVIDUAL = "JSON_GAZE_MULTI_INDIVIDUAL"
    GAZE_STOP = "GAZE_STOP"

    # Share content types
    TEXT = "TEXT"
    URL_IMAGE = "URL_IMAGE"
    URL_VIDEO = "URL_VIDEO"


class GazeMode(str, Enum):
    """Gaze modes for HARU_GAZE actions."""

    TRACK_PERSON = "TRACK_PERSON"
    GROUP = "GROUP"


class ShareMode(str, Enum):
    """Share modes for HARU_SHARE actions."""

    SHOW_SIMPLE = "SHOW_SIMPLE"
    SHOW_ALL = "SHOW_ALL"


class ShareType(str, Enum):
    """Share types for HARU_SHARE actions."""

    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    TEXT = "TEXT"


class ShareSubtype(str, Enum):
    """Share subtypes for HARU_SHARE actions."""

    APP_CONTENT = "APP_CONTENT"
    SHARED_CONTENT = "SHARED_CONTENT"


class RequestType(str, Enum):
    """Request types for HARU_REQUEST actions."""

    IMAGE_AVATAR = "IMAGE_AVATAR"
    IMAGE_PHOTO = "IMAGE_PHOTO"
    TEXT = "TEXT"


class UserId(BaseModel):
    """User identifier for targeting specific users."""

    haru_id: str = Field(..., description="Haru ID (e.g., 'haru-jp')")
    local_id: int = Field(..., description="Local user ID (-1 for all)")


class TTSEntry(BaseModel):
    """TTS entry for CONVERSATE content."""

    tts: str = Field(..., description="Text to speak")
    delay: float = Field(default=1, description="Delay before speaking")
    routine: Optional[int] = Field(default=None, description="Routine ID for animation")


class GazeTarget(BaseModel):
    """Single gaze target for multi-individual gaze."""

    user_id: str = Field(..., description="User ID to gaze at")
    duration: int = Field(..., description="Duration in milliseconds")


class MultiGazeValue(BaseModel):
    """Value for JSON_GAZE_MULTI_INDIVIDUAL content type."""

    gaze_targets: list[GazeTarget] = Field(..., description="List of gaze targets")
    loop: bool = Field(default=False, description="Whether to loop through targets")


class ShareVideoArgs(BaseModel):
    """Video arguments for HARU_SHARE."""

    video_loop: bool = Field(default=False, description="Loop the video")
    video_mute: bool = Field(default=False, description="Mute the video")
    video_wait_completion: bool = Field(
        default=False, description="Wait for video to complete"
    )


class ActionContent(BaseModel):
    """Content item for an action."""

    value: Optional[Any] = Field(default=None, description="Content value")
    value_type: Optional[str] = Field(default=None, description="Content type")
    metainfo: Optional[str] = Field(default=None, description="Metadata description")
    user_id: Optional[UserId] = Field(
        default=None, description="Target user for REQUEST/GAZE"
    )

    model_config = {"extra": "allow"}


class GazeArguments(BaseModel):
    """Arguments for HARU_GAZE actions."""

    gaze_mode: GazeMode = Field(
        default=GazeMode.TRACK_PERSON, description="Gaze tracking mode"
    )


class ShareArguments(BaseModel):
    """Arguments for HARU_SHARE actions."""

    share_mode: ShareMode = Field(..., description="How to display shared content")
    share_type: ShareType = Field(..., description="Type of content being shared")
    share_screen: int = Field(default=1, description="Screen to display on")
    share_subtype: ShareSubtype = Field(..., description="Content subtype")
    share_video_args: Optional[ShareVideoArgs] = Field(
        default=None, description="Video-specific arguments"
    )
    share_image_subtype: Optional[str] = Field(
        default=None, description="Image subtype (e.g., 'IMAGE_AVATAR')"
    )


class RequestArguments(BaseModel):
    """Arguments for HARU_REQUEST actions."""

    request_type: RequestType = Field(..., description="Type of request")


class ActionArguments(BaseModel):
    """Container for action-specific arguments."""

    gaze_arguments: Optional[GazeArguments] = Field(
        default=None, description="GAZE action arguments"
    )
    share_arguments: Optional[ShareArguments] = Field(
        default=None, description="SHARE action arguments"
    )
    request_arguments: Optional[RequestArguments] = Field(
        default=None, description="REQUEST action arguments"
    )


class Action(BaseModel):
    """A single action in an episode."""

    action_id: int = Field(..., description="Unique action identifier")
    action_type: ActionType = Field(..., description="Type of action")
    action_content: Union[list[ActionContent], list[dict], str] = Field(
        default_factory=list, description="Action content items"
    )
    action_goal: Optional[str] = Field(
        default=None, description="Goal for the action (JSON string for CONVERSATE)"
    )
    action_arguments: Optional[ActionArguments] = Field(
        default=None, description="Action-specific arguments"
    )
    bond_action_ids: Optional[list[int]] = Field(
        default=None, description="Actions that run in parallel"
    )
    wait_for_action_ids: Optional[list[int]] = Field(
        default=None, description="Actions that must complete first"
    )
    action_results_key: Optional[str] = Field(
        default=None, description="Key for storing action results (REQUEST)"
    )

    def to_dict(self) -> dict:
        """Convert to dict, excluding None values."""
        data = {}
        data["action_id"] = self.action_id
        data["action_type"] = self.action_type.value

        if self.action_goal:
            data["action_goal"] = self.action_goal

        if self.bond_action_ids:
            data["bond_action_ids"] = self.bond_action_ids

        if self.wait_for_action_ids is not None:
            data["wait_for_action_ids"] = self.wait_for_action_ids

        if self.action_arguments:
            args_dict = {}
            if self.action_arguments.gaze_arguments:
                args_dict["gaze_arguments"] = {
                    "gaze_mode": self.action_arguments.gaze_arguments.gaze_mode.value
                }
            if self.action_arguments.share_arguments:
                share = self.action_arguments.share_arguments
                share_dict = {
                    "share_mode": share.share_mode.value,
                    "share_type": share.share_type.value,
                    "share_screen": share.share_screen,
                    "share_subtype": share.share_subtype.value,
                }
                if share.share_video_args:
                    share_dict["share_video_args"] = share.share_video_args.model_dump()
                if share.share_image_subtype:
                    share_dict["share_image_subtype"] = share.share_image_subtype
                args_dict["share_arguments"] = share_dict
            if self.action_arguments.request_arguments:
                args_dict["request_arguments"] = {
                    "request_type": self.action_arguments.request_arguments.request_type.value
                }
            if args_dict:
                data["action_arguments"] = args_dict

        if self.action_results_key:
            data["action_results_key"] = self.action_results_key

        # Handle action_content
        if isinstance(self.action_content, str):
            data["action_content"] = self.action_content
        elif isinstance(self.action_content, list):
            if all(isinstance(c, ActionContent) for c in self.action_content):
                data["action_content"] = [
                    {k: v for k, v in c.model_dump().items() if v is not None}
                    for c in self.action_content
                ]
            else:
                data["action_content"] = self.action_content
        else:
            data["action_content"] = []

        return data
