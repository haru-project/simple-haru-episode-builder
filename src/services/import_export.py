"""Import/Export service for episode JSON files."""

import json
from pathlib import Path
from typing import BinaryIO

from .validation_service import ValidationService, ValidationResult


class ImportExportService:
    """Service for importing and exporting episode JSON."""

    def __init__(self):
        self.validator = ValidationService()

    def import_from_file(self, file: BinaryIO) -> tuple[dict | None, ValidationResult]:
        """Import episode from uploaded file."""
        try:
            content = file.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return None, ValidationResult(
                is_valid=False, errors=[f"Invalid JSON: {str(e)}"]
            )
        except UnicodeDecodeError as e:
            return None, ValidationResult(
                is_valid=False, errors=[f"Invalid encoding: {str(e)}"]
            )

        # Handle array of episodes (legacy format)
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], list):
                # Nested array - take first episode from first array
                data = data[0][0] if data[0] else {}
            elif len(data) > 0:
                data = data[0]
            else:
                return None, ValidationResult(
                    is_valid=False, errors=["Empty episode array"]
                )

        result = self.validator.validate_episode(data)
        return data, result

    def import_from_string(self, json_str: str) -> tuple[dict | None, ValidationResult]:
        """Import episode from JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return None, ValidationResult(
                is_valid=False, errors=[f"Invalid JSON: {str(e)}"]
            )

        # Handle array of episodes
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], list):
                data = data[0][0] if data[0] else {}
            elif len(data) > 0:
                data = data[0]
            else:
                return None, ValidationResult(
                    is_valid=False, errors=["Empty episode array"]
                )

        result = self.validator.validate_episode(data)
        return data, result

    def export_json(self, episode: dict, pretty: bool = True) -> str:
        """Export episode as JSON string."""
        if pretty:
            return json.dumps(episode, indent=4, ensure_ascii=False)
        else:
            return json.dumps(episode, separators=(",", ":"), ensure_ascii=False)

    def export_as_template(self, episode: dict, parameters: dict[str, dict]) -> str:
        """Export episode as a template with parameter definitions."""
        template_episode = episode.copy()
        template_episode["template"] = {"parameters": parameters}
        return json.dumps(template_episode, indent=4, ensure_ascii=False)

    def save_to_file(self, episode: dict, path: Path, pretty: bool = True) -> None:
        """Save episode to file."""
        content = self.export_json(episode, pretty=pretty)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
