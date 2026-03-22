"""Action goal models for structured goal editing."""

from typing import Optional
from pydantic import BaseModel, Field


class Timeout(BaseModel):
    """Timeout configuration for action goals."""

    max_time: Optional[dict] = Field(
        default=None,
        description="Max time with 'minutes' and 'seconds' keys",
    )
    max_turns: Optional[int] = Field(
        default=None,
        description="Maximum number of conversation turns",
    )

    @classmethod
    def create(
        cls, minutes: int = 0, seconds: int = 0, max_turns: Optional[int] = None
    ) -> "Timeout":
        max_time = None
        if minutes > 0 or seconds > 0:
            max_time = {"minutes": minutes, "seconds": seconds}
        return cls(max_time=max_time, max_turns=max_turns)


class SuccessCriterion(BaseModel):
    """A single success criterion for an action goal."""

    id: str = Field(..., description="Unique identifier for criterion (e.g., 'c1')")
    description: str = Field(..., description="Description of what constitutes success")
    reached: bool = Field(default=False, description="Whether criterion has been met")
    evidence: Optional[str] = Field(
        default=None, description="Evidence that criterion was met"
    )


class CriteriaExpandMapping(BaseModel):
    """Single mapping for criteria expansion."""

    source: str = Field(
        ..., description="Source variable (e.g., 'participants_start_right')"
    )
    target: str = Field(..., description="Target variable (e.g., 'participant')")


class CriteriaExpand(BaseModel):
    """Criteria expansion configuration for participant variables."""

    ids: list[str] = Field(
        ..., description="List of criterion IDs to expand (e.g., ['c1', 'c2'])"
    )
    mappings: list[CriteriaExpandMapping] = Field(
        ..., description="Variable mappings for expansion"
    )


class ActionGoal(BaseModel):
    """Structured action goal with success criteria and timeout."""

    id: str = Field(..., description="Goal identifier")
    description: str = Field(..., description="Goal description")
    success_criteria: list[SuccessCriterion] = Field(
        default_factory=list, description="List of success criteria"
    )
    criteria_expand: list[CriteriaExpand] = Field(
        default_factory=list, description="Criteria expansion configurations"
    )
    timeout: Optional[Timeout] = Field(default=None, description="Timeout settings")
    additional_instructions: list[str] = Field(
        default_factory=list, description="Additional instructions for the agent"
    )

    def to_json_string(self) -> str:
        """Convert to JSON string for action_goal field."""
        import json

        return json.dumps(self.model_dump(exclude_none=True))

    @classmethod
    def from_json_string(cls, json_str: str) -> "ActionGoal":
        """Parse from JSON string."""
        import json

        data = json.loads(json_str)
        return cls.model_validate(data)

    @classmethod
    def try_parse(cls, value: str) -> Optional["ActionGoal"]:
        """Try to parse a string as ActionGoal, return None if not valid JSON goal."""
        if not value or not value.strip().startswith("{"):
            return None
        try:
            return cls.from_json_string(value)
        except Exception:
            return None
