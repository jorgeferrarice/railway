"""Checks on template definitions that the JSON Schema cannot express."""

from __future__ import annotations

import re

SECRET_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Characters that would corrupt an ADO.NET connection string if a generated
# secret happened to contain them.
FORBIDDEN_SECRET_CHARS = set(";=")

# Variables Railway injects into every service; they are never declared in a
# template definition but are legal reference targets.
RAILWAY_PROVIDED = {
    "RAILWAY_PRIVATE_DOMAIN",
    "RAILWAY_PUBLIC_DOMAIN",
    "RAILWAY_TCP_PROXY_DOMAIN",
    "RAILWAY_TCP_PROXY_PORT",
    "RAILWAY_STATIC_URL",
    "RAILWAY_SERVICE_NAME",
    "RAILWAY_PROJECT_NAME",
    "RAILWAY_ENVIRONMENT_NAME",
    "PORT",
}

# Registries whose images this repository always pins by digest, because the
# upstream project publishes no immutable version tags.
DIGEST_ONLY_IMAGES = ("ghcr.io/aptabase/aptabase",)

CROSS_SERVICE_REFERENCE = re.compile(r"\$\{\{\s*([a-z][a-z0-9-]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
SECRET_CALL = re.compile(r"\$\{\{\s*secret\(([^)]*)\)\s*\}\}")
SECRET_ALPHABET_ARG = re.compile(r'"([^"]*)"')


def lint_template(template: dict) -> list[str]:
    """Return every problem found in the template. Empty list means clean."""
    services = template.get("services", [])
    declared = {
        service["name"]: set(service.get("variables", {}))
        for service in services
        if isinstance(service, dict) and isinstance(service.get("name"), str)
    }

    problems: list[str] = []
    for service in services:
        problems.extend(_lint_image(service))
        for name, variable in service.get("variables", {}).items():
            where = f"{service['name']}.{name}"
            value = variable.get("value", "")
            problems.extend(_lint_references(where, value, declared))
            problems.extend(_lint_secrets(where, value))
    return problems


def _lint_image(service: dict) -> list[str]:
    source = service.get("source", {})
    if source.get("type") != "image":
        return []
    image = source.get("image", "")
    for prefix in DIGEST_ONLY_IMAGES:
        if image.startswith(prefix) and "@sha256:" not in image:
            return [
                f"{service['name']}: {prefix} publishes no version tags, "
                f"so it must be pinned by digest, got {image!r}"
            ]
    return []


def _lint_references(where: str, value: str, declared: dict[str, set[str]]) -> list[str]:
    problems = []
    for service_name, variable_name in CROSS_SERVICE_REFERENCE.findall(value):
        if service_name not in declared:
            problems.append(f"{where}: references unknown service {service_name!r}")
        elif (
            variable_name not in declared[service_name]
            and variable_name not in RAILWAY_PROVIDED
        ):
            problems.append(
                f"{where}: references {variable_name!r}, which service "
                f"{service_name!r} does not define"
            )
    return problems


def _lint_secrets(where: str, value: str) -> list[str]:
    problems = []
    for args in SECRET_CALL.findall(value):
        alphabet_match = SECRET_ALPHABET_ARG.search(args)
        if alphabet_match is None:
            problems.append(
                f"{where}: secret() must pass an explicit alphabet; Railway's "
                f"default may emit connection-string delimiters"
            )
            continue
        bad = sorted(set(alphabet_match.group(1)) & FORBIDDEN_SECRET_CHARS)
        if bad:
            problems.append(
                f"{where}: secret() alphabet contains {''.join(bad)!r}, which "
                f"would corrupt an ADO.NET connection string"
            )
    return problems
