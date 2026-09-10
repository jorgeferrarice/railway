"""Load and validate Railway template definitions."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "template.schema.json"


class TemplateValidationError(ValueError):
    """Raised when a template definition does not match the schema."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    """Read the template JSON Schema from disk."""
    return json.loads(path.read_text())


def validate_template(template: dict, schema: dict | None = None) -> None:
    """Raise TemplateValidationError if the template does not match the schema.

    Reports every problem found, not only the first, so a single run tells the
    author everything that needs fixing.
    """
    validator = Draft202012Validator(schema if schema is not None else load_schema())
    errors = [
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(template), key=lambda e: list(e.absolute_path))
    ]
    errors.extend(_duplicate_service_errors(template))
    if errors:
        raise TemplateValidationError(errors)


def _duplicate_service_errors(template: dict) -> list[str]:
    """Service names address variable references, so they must be unique.

    JSON Schema cannot express uniqueness on an object property, so it is
    checked here.
    """
    services = template.get("services")
    if not isinstance(services, list):
        return []
    names = [s["name"] for s in services if isinstance(s, dict) and isinstance(s.get("name"), str)]
    return [
        f"services: duplicate service name {name!r}"
        for name, count in Counter(names).items()
        if count > 1
    ]


def load_template(path: Path) -> dict:
    """Read a template definition from disk and validate it."""
    template = json.loads(Path(path).read_text())
    validate_template(template)
    return template
