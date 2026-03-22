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

    _FILLER_WORDS = {"a", "an", "the", "your", "their", "my", "our", "his", "her", "its"}
    _MAX_ID_LENGTH = 40

    @classmethod
    def _to_snake_case(cls, text: str) -> str:
        """Convert text to a snake_case identifier."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        words = [w for w in text.split() if w not in cls._FILLER_WORDS]
        text = "_".join(words)
        text = re.sub(r"_+", "_", text)
        # Truncate at word boundary
        if len(text) > cls._MAX_ID_LENGTH:
            text = text[:cls._MAX_ID_LENGTH].rsplit("_", 1)[0]
        return text.strip("_")

    def substitute_parameters(self, template_data: dict, params: dict[str, str]) -> dict:
        """Substitute {param} placeholders with actual values."""
        # Auto-generate derived parameters
        derived = template_data.get("template", {}).get("derived", {})
        for key, rule in derived.items():
            source_value = params.get(rule["from"], "")
            if rule.get("transform") == "snake_case":
                params[key] = self._to_snake_case(source_value)

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
