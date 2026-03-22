"""Validation service for episode JSON."""

import json
from dataclasses import dataclass, field
from typing import Any

from ..utils.constants import ACTION_TYPES, CONTENT_TYPES_BY_ACTION, GAZE_MODES


@dataclass
class ValidationResult:
    """Result of validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ValidationService:
    """Service for validating episode JSON."""

    REQUIRED_EPISODE_FIELDS = [
        "app_id",
        "episode_id",
        "haru_id",
        "stage_id",
        "task_id",
        "actions",
    ]

    REQUIRED_ACTION_FIELDS = ["action_id", "action_type"]

    def validate_episode(self, data: dict | str) -> ValidationResult:
        """Validate an episode dictionary or JSON string."""
        errors = []
        warnings = []

        # Parse if string
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                return ValidationResult(
                    is_valid=False, errors=[f"Invalid JSON: {str(e)}"]
                )

        # Check required fields
        for field_name in self.REQUIRED_EPISODE_FIELDS:
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")

        # Validate types
        if "stage_id" in data and not isinstance(data["stage_id"], int):
            errors.append("stage_id must be an integer")
        if "task_id" in data and not isinstance(data["task_id"], int):
            errors.append("task_id must be an integer")
        if "actions" in data and not isinstance(data["actions"], list):
            errors.append("actions must be a list")
        elif "actions" in data:
            # Validate each action
            action_ids = set()
            for i, action in enumerate(data["actions"]):
                action_result = self.validate_action(action, i)
                errors.extend(action_result.errors)
                warnings.extend(action_result.warnings)

                # Check for duplicate action IDs
                action_id = action.get("action_id")
                if action_id is not None:
                    if action_id in action_ids:
                        warnings.append(f"Duplicate action_id: {action_id}")
                    action_ids.add(action_id)

            # Check bond/wait references
            for action in data["actions"]:
                for ref_id in action.get("bond_action_ids", []):
                    if ref_id not in action_ids:
                        warnings.append(
                            f"Action {action.get('action_id')}: bond_action_ids references non-existent action {ref_id}"
                        )
                for ref_id in action.get("wait_for_action_ids", []):
                    if ref_id not in action_ids:
                        warnings.append(
                            f"Action {action.get('action_id')}: wait_for_action_ids references non-existent action {ref_id}"
                        )

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_action(self, action: dict, index: int) -> ValidationResult:
        """Validate a single action."""
        errors = []
        warnings = []
        prefix = f"Action #{index + 1}"

        # Check required fields
        for field_name in self.REQUIRED_ACTION_FIELDS:
            if field_name not in action:
                errors.append(f"{prefix}: Missing required field: {field_name}")

        # Validate action_type
        action_type = action.get("action_type")
        if action_type and action_type not in ACTION_TYPES:
            errors.append(f"{prefix}: Invalid action_type: {action_type}")

        # Validate action_id is integer
        action_id = action.get("action_id")
        if action_id is not None and not isinstance(action_id, int):
            errors.append(f"{prefix}: action_id must be an integer")

        # Type-specific validation
        if action_type == "HARU_GAZE":
            result = self._validate_gaze_action(action, prefix)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif action_type == "HARU_SHARE":
            result = self._validate_share_action(action, prefix)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif action_type == "HARU_REQUEST":
            result = self._validate_request_action(action, prefix)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif action_type == "HARU_CONVERSATE":
            result = self._validate_conversate_action(action, prefix)
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_gaze_action(self, action: dict, prefix: str) -> ValidationResult:
        """Validate HARU_GAZE specific fields."""
        errors = []
        warnings = []

        args = action.get("action_arguments", {})
        gaze_args = args.get("gaze_arguments", {})

        if not gaze_args:
            warnings.append(f"{prefix}: HARU_GAZE should have gaze_arguments")
        else:
            gaze_mode = gaze_args.get("gaze_mode")
            if gaze_mode and gaze_mode not in GAZE_MODES:
                errors.append(f"{prefix}: Invalid gaze_mode: {gaze_mode}")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_share_action(self, action: dict, prefix: str) -> ValidationResult:
        """Validate HARU_SHARE specific fields."""
        errors = []
        warnings = []

        args = action.get("action_arguments", {})
        share_args = args.get("share_arguments", {})

        if not share_args:
            warnings.append(f"{prefix}: HARU_SHARE should have share_arguments")
        else:
            required_share_fields = ["share_mode", "share_type"]
            for field_name in required_share_fields:
                if field_name not in share_args:
                    warnings.append(
                        f"{prefix}: share_arguments missing {field_name}"
                    )

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_request_action(self, action: dict, prefix: str) -> ValidationResult:
        """Validate HARU_REQUEST specific fields."""
        errors = []
        warnings = []

        args = action.get("action_arguments", {})
        request_args = args.get("request_arguments", {})

        if not request_args:
            warnings.append(f"{prefix}: HARU_REQUEST should have request_arguments")
        elif "request_type" not in request_args:
            warnings.append(f"{prefix}: request_arguments missing request_type")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_conversate_action(
        self, action: dict, prefix: str
    ) -> ValidationResult:
        """Validate HARU_CONVERSATE specific fields."""
        errors = []
        warnings = []

        # Validate action_goal if present
        action_goal = action.get("action_goal")
        if action_goal and isinstance(action_goal, str):
            if action_goal.strip().startswith("{"):
                try:
                    goal_data = json.loads(action_goal)
                    # Validate goal structure
                    if "success_criteria" in goal_data:
                        if not isinstance(goal_data["success_criteria"], list):
                            errors.append(
                                f"{prefix}: action_goal.success_criteria must be a list"
                            )
                except json.JSONDecodeError:
                    errors.append(f"{prefix}: action_goal contains invalid JSON")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_goal_json(self, goal_str: str) -> ValidationResult:
        """Validate a structured goal JSON string."""
        errors = []
        warnings = []

        try:
            goal = json.loads(goal_str)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False, errors=[f"Invalid JSON: {str(e)}"]
            )

        # Check required fields
        if "id" not in goal:
            warnings.append("Goal missing 'id' field")
        if "description" not in goal:
            warnings.append("Goal missing 'description' field")

        # Validate success_criteria
        criteria = goal.get("success_criteria", [])
        if criteria:
            criterion_ids = set()
            for i, c in enumerate(criteria):
                if "id" not in c:
                    errors.append(f"Criterion #{i + 1} missing 'id'")
                else:
                    if c["id"] in criterion_ids:
                        warnings.append(f"Duplicate criterion id: {c['id']}")
                    criterion_ids.add(c["id"])
                if "description" not in c:
                    errors.append(f"Criterion #{i + 1} missing 'description'")

            # Validate criteria_expand references
            for expand in goal.get("criteria_expand", []):
                for ref_id in expand.get("ids", []):
                    if ref_id not in criterion_ids:
                        warnings.append(
                            f"criteria_expand references non-existent criterion: {ref_id}"
                        )

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )
