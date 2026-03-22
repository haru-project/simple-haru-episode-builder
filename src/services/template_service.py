"""Template loading and parameter substitution service."""

import json
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TemplateInfo:
    """Information about a template file."""

    name: str
    path: Path
    parameters: dict[str, dict]
    description: str


class TemplateService:
    """Service for handling episode templates."""

    def __init__(self, template_dir: Path | str):
        self.template_dir = Path(template_dir)

    def list_templates(self) -> list[TemplateInfo]:
        """List all available templates."""
        templates = []
        if not self.template_dir.exists():
            return templates

        for json_file in self.template_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                # Check if it's a template (has template field)
                template_info = data.get("template", {})
                parameters = template_info.get("parameters", {})

                # Only use explicitly defined parameters from template.parameters
                if "template" in data:
                    templates.append(
                        TemplateInfo(
                            name=json_file.stem,
                            path=json_file,
                            parameters=parameters,
                            description=data.get("description", ""),
                        )
                    )
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(templates, key=lambda t: t.name)

    def _detect_parameters(self, data: dict) -> dict[str, dict]:
        """Detect {param} placeholders in the template data."""
        content = json.dumps(data)
        # Find all {param} patterns
        params = set(re.findall(r"\{(\w+)\}", content))
        # Exclude common false positives
        exclude = {"robot_name", "participant", "participants_count"}
        params = params - exclude

        return {
            p: {"description": f"Parameter: {p}", "example": ""} for p in sorted(params)
        }

    def load_template(self, template_path: Path) -> dict:
        """Load a template file."""
        with open(template_path, "r") as f:
            return json.load(f)

    def substitute_parameters(self, template_data: dict, params: dict[str, str]) -> dict:
        """Substitute {param} placeholders with actual values."""
        # Convert to string, substitute, convert back
        content = json.dumps(template_data, ensure_ascii=False)

        for key, value in params.items():
            content = content.replace(f"{{{key}}}", value)

        result = json.loads(content)

        # Remove template metadata from result
        if "template" in result:
            del result["template"]

        return result

    def get_required_parameters(self, template_data: dict) -> dict[str, dict]:
        """Get required parameters from template."""
        # First check explicit template definition
        if "template" in template_data:
            return template_data["template"].get("parameters", {})

        # Otherwise detect from content
        return self._detect_parameters(template_data)

    def validate_parameters(
        self, template_data: dict, params: dict[str, str]
    ) -> list[str]:
        """Validate that all required parameters are provided."""
        required = self.get_required_parameters(template_data)
        errors = []

        for param_name in required:
            if not params.get(param_name):
                errors.append(f"Missing required parameter: {param_name}")

        return errors
