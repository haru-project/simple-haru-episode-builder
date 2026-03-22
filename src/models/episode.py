"""Episode model for Haru interactions."""

from typing import Optional
from pydantic import BaseModel, Field
from .actions import Action


class TemplateParameter(BaseModel):
    """Parameter definition for templates."""

    description: str = Field(..., description="Parameter description")
    example: str = Field(..., description="Example value")


class Template(BaseModel):
    """Template metadata for episode templates."""

    parameters: dict[str, TemplateParameter] = Field(
        default_factory=dict, description="Template parameters"
    )


class Episode(BaseModel):
    """A complete Haru episode."""

    app_id: str = Field(default="test", description="Application identifier")
    episode_id: str = Field(default="1", description="Episode identifier")
    haru_id: str = Field(default="haru-jp", description="Haru robot identifier")
    stage_id: int = Field(default=1, description="Stage number")
    task_id: int = Field(default=1, description="Task number")
    ready: bool = Field(default=False, description="Whether episode is ready")
    mute: bool = Field(default=True, description="Whether to mute audio")
    teleconference_on: bool = Field(
        default=True, description="Whether teleconference is enabled"
    )
    description: str = Field(default="", description="Episode description")
    actions: list[Action] = Field(default_factory=list, description="List of actions")
    gaze_mode: Optional[str] = Field(
        default=None, description="Default gaze mode for episode"
    )
    template: Optional[Template] = Field(
        default=None, description="Template metadata if this is a template"
    )

    def to_dict(self) -> dict:
        """Convert to dict for JSON export."""
        data = {
            "app_id": self.app_id,
            "episode_id": self.episode_id,
            "haru_id": self.haru_id,
            "stage_id": self.stage_id,
            "task_id": self.task_id,
            "ready": self.ready,
            "mute": self.mute,
            "teleconference_on": self.teleconference_on,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
        }
        if self.gaze_mode:
            data["gaze_mode"] = self.gaze_mode
        if self.template:
            data["template"] = self.template.model_dump()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Episode":
        """Create Episode from dict."""
        actions = []
        for a in data.get("actions", []):
            actions.append(Action.model_validate(a))
        return cls(
            app_id=data.get("app_id", "test"),
            episode_id=data.get("episode_id", "1"),
            haru_id=data.get("haru_id", "haru-jp"),
            stage_id=data.get("stage_id", 1),
            task_id=data.get("task_id", 1),
            ready=data.get("ready", False),
            mute=data.get("mute", True),
            teleconference_on=data.get("teleconference_on", True),
            description=data.get("description", ""),
            actions=actions,
            gaze_mode=data.get("gaze_mode"),
            template=Template.model_validate(data["template"])
            if data.get("template")
            else None,
        )
