"""Template loading and rendering utilities."""

import importlib.resources
import re


def load_template(relative_path: str) -> str:
    """Load a template file from the bundled templates directory."""
    resource = importlib.resources.files("pyptmpl") / "templates"
    for part in relative_path.split("/"):
        resource = resource / part
    return resource.read_text(encoding="utf-8")


def render_template(template: str, **kwargs: str) -> str:
    """Replace {{KEY}} placeholders in template with provided values."""
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", value)
    unresolved = sorted(set(re.findall(r"\{\{[a-z_][a-z0-9_]*\}\}", template)))
    if unresolved:
        unresolved_list = ", ".join(unresolved)
        raise ValueError(f"Unresolved template placeholders: {unresolved_list}")
    return template
