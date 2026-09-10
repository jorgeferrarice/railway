# Aptabase Railway Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, verify and publish a Railway marketplace template that deploys a self-hosted Aptabase instance from a version-controlled definition in `~/Personal/railway`.

**Architecture:** A new git monorepo holds one directory per Railway template. Each template is described by a repository-owned `template.json` validated against a JSON Schema and linted for cross-service reference integrity. A Python CLI (`scripts/railway_template.py`) translates that file into Railway GraphQL API calls to create, update, publish and deploy the template. Aptabase itself is three services: Railway's Postgres image, a ClickHouse image built from this repo with Railway-specific tuning, and the upstream Aptabase application image pinned by digest.

**Tech Stack:** Python 3.11 (stdlib `urllib` + `argparse`), `jsonschema` for validation, `pytest` for tests, Docker for verifying the ClickHouse image locally, Railway GraphQL API v2, GitHub for hosting the repository that Railway builds the ClickHouse service from.

**Spec:** `docs/superpowers/specs/2026-09-10-aptabase-railway-template-design.md`

## Global Constraints

- Python 3.11.7 is the interpreter on this machine. Do not use syntax newer than 3.11.
- All Python dependencies live in a repo-local virtualenv at `.venv/`, installed from `requirements-dev.txt`. Never install into the system interpreter.
- Aptabase application image: `ghcr.io/aptabase/aptabase@sha256:8efa3c0b451947c296410855666fb4ec8e812ddd15e4f236984284a6ad8510fe`. Digest-pinned always; a bare `:main` tag is a lint failure.
- PostgreSQL image: `ghcr.io/railwayapp-templates/postgres-ssl:15.19`. Exact tag, no floating major.
- ClickHouse base image: `clickhouse/clickhouse-server:23.8.4.69-alpine`. Exact tag.
- Aptabase service listens on port `8080`, health path `/healthz`, health check timeout `300` seconds.
- Generated secrets use the alphabet `abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789` and length `32`. No other characters — `;` and `=` are ADO.NET connection-string delimiters.
- `CLICKHOUSE_DB` is never set. Aptabase writes to the ClickHouse `default` database, matching upstream.
- The Railway API token is read from the `RAILWAY_API_TOKEN` environment variable only. Never read `~/.railway/config.json`.
- Railway API endpoint: `https://backboard.railway.com/graphql/v2`.
- Service names in the template are exactly `postgres`, `clickhouse`, `aptabase` — variable references depend on these strings.
- Repository baseline required before the work is called done: caveman rule files, `RTK.md` at the repository root, `graphify-out/graph.json`.
- Tasks 12 and 13 are outward-facing (a GitHub push, a billable Railway deploy). They run **only** on explicit instruction from the user.

### Deviation from the spec

The spec names the digest bumper `templates/aptabase/bump-digest.sh`. This plan implements it as `scripts/bump_digest.py` instead: it is unit-testable, and every future template in this monorepo needs the same capability. The behaviour is identical.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `.gitignore` | Ignore `.venv/`, `__pycache__/`, `.pytest_cache/` |
| `README.md` | Index of templates in this monorepo |
| `RTK.md` | Copy of `~/.claude/RTK.md` — repository baseline requirement |
| `requirements-dev.txt` | `jsonschema`, `pytest` |
| `pyproject.toml` | pytest configuration, `pythonpath = ["scripts"]` |
| `schema/template.schema.json` | JSON Schema for every `template.json` in this repo |
| `scripts/rt_schema.py` | Load and schema-validate a template definition |
| `scripts/rt_lint.py` | Cross-service reference and invariant checks |
| `scripts/rt_api.py` | Railway GraphQL transport, auth, introspection |
| `scripts/rt_payload.py` | `template.json` → Railway API payload |
| `scripts/bump_digest.py` | Re-resolve a pinned image digest from its registry |
| `scripts/railway_template.py` | CLI entry point dispatching to the modules above |
| `templates/aptabase/template.json` | The Aptabase service graph |
| `templates/aptabase/README.md` | Deploy guide and marketplace listing copy |
| `templates/aptabase/clickhouse/Dockerfile` | ClickHouse image with Railway tuning |
| `templates/aptabase/clickhouse/config.d/railway.xml` | The tuning itself |
| `templates/aptabase/clickhouse/railway.json` | Railway build/deploy config for that service |
| `docs/railway-template-api.md` | Recorded GraphQL input types (output of Task 8) |
| `tests/test_rt_schema.py` | Schema loading and validation |
| `tests/test_rt_lint.py` | Reference and invariant linting |
| `tests/test_aptabase_template.py` | The real template passes schema + lint, spec invariants hold |
| `tests/test_bump_digest.py` | Digest resolution and in-place rewrite |
| `tests/test_rt_api.py` | Auth, transport, error handling, introspection |
| `tests/test_rt_payload.py` | Payload construction |
| `tests/test_clickhouse_image.py` | Docker build + runtime assertions |

---

## Task 1: Repository scaffolding and baseline

**Files:**
- Create: `.gitignore`, `README.md`, `RTK.md`, `requirements-dev.txt`, `pyproject.toml`
- Create: `AGENTS.md`, `.cursor/rules/caveman.mdc`, `.windsurf/rules/caveman.md`, `.clinerules/caveman.md`, `.opencode/AGENTS.md`, `.github/copilot-instructions.md` (generated by `/caveman-init`)

**Interfaces:**
- Consumes: nothing
- Produces: a `.venv/` with `pytest` and `jsonschema` importable; `pytest` runnable from the repository root with `scripts/` on the import path

- [ ] **Step 1: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
```

- [ ] **Step 2: Write `requirements-dev.txt`**

```text
jsonschema==4.23.0
pytest==8.3.4
```

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["scripts"]
addopts = "-q"
```

- [ ] **Step 4: Write `README.md`**

```markdown
# Railway templates

Version-controlled [Railway](https://railway.com) template definitions.

Each template lives in `templates/<name>/` and is described by a `template.json`
validated against `schema/template.schema.json`. `scripts/railway_template.py`
turns those definitions into Railway API calls.

## Templates

| Template | Description |
| --- | --- |
| [aptabase](templates/aptabase/) | Self-hosted Aptabase — open-source analytics for mobile, desktop and web apps |

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

## Documentation

- [RTK](RTK.md)
- [Design specs](docs/superpowers/specs/)
- [Implementation plans](docs/superpowers/plans/)
```

- [ ] **Step 5: Copy the RTK documentation into the repository**

Run: `cp ~/.claude/RTK.md /Users/ferrari/Personal/railway/RTK.md`
Expected: `RTK.md` exists at the repository root. This is a hard repository-baseline requirement.

- [ ] **Step 6: Install the caveman rule files, dry run first**

Run the `/caveman-init --dry-run` slash command in this repository. Read the reported plan. No file in this repository pre-exists, so no `--force` is needed.
Expected: the dry run lists `AGENTS.md`, `.cursor/rules/caveman.mdc`, `.windsurf/rules/caveman.md`, `.clinerules/caveman.md`, `.opencode/AGENTS.md`, `.github/copilot-instructions.md` as creations, zero overwrites.

- [ ] **Step 7: Apply the caveman rule files**

Run the `/caveman-init` slash command in this repository.
Expected: the six rule files exist and each contains the caveman activation rule.

- [ ] **Step 8: Create the virtualenv and install dependencies**

```bash
cd /Users/ferrari/Personal/railway
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Expected: `jsonschema` and `pytest` install without error.

- [ ] **Step 9: Verify pytest runs against an empty suite**

Run: `.venv/bin/pytest`
Expected: exit code 5, `no tests ran`. This confirms the config is picked up. Exit code 5 is success for this step.

- [ ] **Step 10: Commit**

```bash
git add .gitignore README.md RTK.md requirements-dev.txt pyproject.toml AGENTS.md .cursor .windsurf .clinerules .opencode .github
git commit -m "chore: scaffold the railway templates monorepo

Adds the repository baseline (RTK.md, caveman rule files), the Python
dev environment, and pytest configuration.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: Template schema and validator

**Files:**
- Create: `schema/template.schema.json`
- Create: `scripts/rt_schema.py`
- Test: `tests/test_rt_schema.py`

**Interfaces:**
- Consumes: the virtualenv from Task 1
- Produces:
  - `rt_schema.SCHEMA_PATH: pathlib.Path`
  - `rt_schema.TemplateValidationError(ValueError)` with attribute `errors: list[str]`
  - `rt_schema.load_schema(path: Path = SCHEMA_PATH) -> dict`
  - `rt_schema.validate_template(template: dict, schema: dict | None = None) -> None` — raises `TemplateValidationError`
  - `rt_schema.load_template(path: Path) -> dict` — reads JSON, validates, returns the parsed dict

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rt_schema.py`:

```python
import json

import pytest

import rt_schema


def minimal_template():
    return {
        "name": "Example",
        "description": "An example template.",
        "category": "Analytics",
        "services": [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"PORT": {"value": "8080"}},
            }
        ],
    }


def test_load_schema_returns_a_draft_2020_12_schema():
    schema = rt_schema.load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_minimal_template_validates():
    rt_schema.validate_template(minimal_template())


def test_missing_name_is_rejected():
    template = minimal_template()
    del template["name"]
    with pytest.raises(rt_schema.TemplateValidationError) as excinfo:
        rt_schema.validate_template(template)
    assert any("name" in error for error in excinfo.value.errors)


def test_unknown_source_type_is_rejected():
    template = minimal_template()
    template["services"][0]["source"] = {"type": "helm", "chart": "nope"}
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.validate_template(template)


def test_repo_source_requires_a_root_directory():
    template = minimal_template()
    template["services"][0]["source"] = {"type": "repo", "repo": "owner/name"}
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.validate_template(template)


def test_variable_value_must_be_a_string():
    template = minimal_template()
    template["services"][0]["variables"]["PORT"] = {"value": 8080}
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.validate_template(template)


def test_duplicate_service_names_are_rejected():
    template = minimal_template()
    template["services"].append(dict(template["services"][0]))
    with pytest.raises(rt_schema.TemplateValidationError) as excinfo:
        rt_schema.validate_template(template)
    assert any("duplicate" in error.lower() for error in excinfo.value.errors)


def test_all_errors_are_reported_not_just_the_first():
    template = minimal_template()
    del template["name"]
    del template["description"]
    with pytest.raises(rt_schema.TemplateValidationError) as excinfo:
        rt_schema.validate_template(template)
    assert len(excinfo.value.errors) >= 2


def test_load_template_reads_and_validates(tmp_path):
    path = tmp_path / "template.json"
    path.write_text(json.dumps(minimal_template()))
    assert rt_schema.load_template(path)["name"] == "Example"


def test_load_template_raises_on_an_invalid_file(tmp_path):
    path = tmp_path / "template.json"
    path.write_text(json.dumps({"name": "Broken"}))
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.load_template(path)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_rt_schema.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'rt_schema'`.

- [ ] **Step 3: Write the JSON Schema**

Create `schema/template.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/jorgeferrarice/railway/schema/template.schema.json",
  "title": "Railway template definition",
  "type": "object",
  "required": ["name", "description", "category", "services"],
  "additionalProperties": false,
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "description": {"type": "string", "minLength": 1},
    "category": {"type": "string", "minLength": 1},
    "readme": {"type": "string", "minLength": 1},
    "links": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["label", "url"],
        "additionalProperties": false,
        "properties": {
          "label": {"type": "string", "minLength": 1},
          "url": {"type": "string", "format": "uri"}
        }
      }
    },
    "services": {
      "type": "array",
      "minItems": 1,
      "items": {"$ref": "#/$defs/service"}
    }
  },
  "$defs": {
    "service": {
      "type": "object",
      "required": ["name", "source"],
      "additionalProperties": false,
      "properties": {
        "name": {"type": "string", "pattern": "^[a-z][a-z0-9-]*$"},
        "source": {
          "oneOf": [
            {"$ref": "#/$defs/imageSource"},
            {"$ref": "#/$defs/repoSource"}
          ]
        },
        "variables": {
          "type": "object",
          "additionalProperties": {"$ref": "#/$defs/variable"},
          "propertyNames": {"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"}
        },
        "volumes": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["mountPath"],
            "additionalProperties": false,
            "properties": {
              "mountPath": {"type": "string", "pattern": "^/"}
            }
          }
        },
        "networking": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "http": {
              "type": "object",
              "required": ["targetPort"],
              "additionalProperties": false,
              "properties": {
                "targetPort": {"type": "integer", "minimum": 1, "maximum": 65535}
              }
            }
          }
        },
        "deploy": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "healthcheckPath": {"type": "string", "pattern": "^/"},
            "healthcheckTimeout": {"type": "integer", "minimum": 1},
            "restartPolicyType": {"enum": ["ON_FAILURE", "ALWAYS", "NEVER"]},
            "restartPolicyMaxRetries": {"type": "integer", "minimum": 0}
          }
        }
      }
    },
    "imageSource": {
      "type": "object",
      "required": ["type", "image"],
      "additionalProperties": false,
      "properties": {
        "type": {"const": "image"},
        "image": {"type": "string", "minLength": 1}
      }
    },
    "repoSource": {
      "type": "object",
      "required": ["type", "repo", "rootDirectory"],
      "additionalProperties": false,
      "properties": {
        "type": {"const": "repo"},
        "repo": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
        "rootDirectory": {"type": "string", "minLength": 1},
        "branch": {"type": "string", "minLength": 1}
      }
    },
    "variable": {
      "type": "object",
      "required": ["value"],
      "additionalProperties": false,
      "properties": {
        "value": {"type": "string"},
        "description": {"type": "string"},
        "isOptional": {"type": "boolean"}
      }
    }
  }
}
```

- [ ] **Step 4: Write `scripts/rt_schema.py`**

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_rt_schema.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add schema/template.schema.json scripts/rt_schema.py tests/test_rt_schema.py
git commit -m "feat: add the template definition schema and validator

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Template linter

**Files:**
- Create: `scripts/rt_lint.py`
- Test: `tests/test_rt_lint.py`

**Interfaces:**
- Consumes: `rt_schema.load_template`
- Produces:
  - `rt_lint.SECRET_ALPHABET: str`
  - `rt_lint.lint_template(template: dict) -> list[str]` — returns human-readable problems, empty list when clean

The linter catches what the schema structurally cannot: a `${{service.VAR}}` reference to a service or variable that does not exist, a floating image tag where a digest is required, and a `secret()` call whose alphabet can emit connection-string delimiters.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rt_lint.py`:

```python
import rt_lint


def template_with(services):
    return {
        "name": "Example",
        "description": "An example template.",
        "category": "Analytics",
        "services": services,
    }


def test_a_clean_template_reports_nothing():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": "hunter2"}},
            },
            {
                "name": "app",
                "source": {
                    "type": "image",
                    "image": "ghcr.io/example/app@sha256:" + "a" * 64,
                },
                "variables": {
                    "DB": {"value": "Password=${{db.PASSWORD}};Host=${{db.RAILWAY_PRIVATE_DOMAIN}}"}
                },
            },
        ]
    )
    assert rt_lint.lint_template(template) == []


def test_reference_to_an_unknown_service_is_reported():
    template = template_with(
        [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"DB": {"value": "${{cache.PASSWORD}}"}},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("cache" in problem for problem in problems)


def test_reference_to_an_unknown_variable_is_reported():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": "hunter2"}},
            },
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"DB": {"value": "${{db.USERNAME}}"}},
            },
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("USERNAME" in problem for problem in problems)


def test_railway_provided_variables_are_not_treated_as_unknown():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {},
            },
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"HOST": {"value": "${{db.RAILWAY_PRIVATE_DOMAIN}}"}},
            },
        ]
    )
    assert rt_lint.lint_template(template) == []


def test_unqualified_reference_to_an_own_variable_is_allowed():
    template = template_with(
        [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {
                    "PORT": {"value": "8080"},
                    "URL": {"value": "http://localhost:${{PORT}}"},
                },
            }
        ]
    )
    assert rt_lint.lint_template(template) == []


def test_secret_alphabet_with_delimiters_is_reported():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": '${{secret(32, "abc;=")}}'}},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("alphabet" in problem for problem in problems)


def test_secret_without_an_explicit_alphabet_is_reported():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": "${{secret(32)}}"}},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("alphabet" in problem for problem in problems)


def test_floating_tag_on_a_digest_pinned_registry_is_reported():
    template = template_with(
        [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/aptabase/aptabase:main"},
                "variables": {},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("digest" in problem for problem in problems)


def test_a_service_with_a_volume_and_no_mount_path_conflict_is_clean():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {},
                "volumes": [{"mountPath": "/var/lib/db"}],
            }
        ]
    )
    assert rt_lint.lint_template(template) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_rt_lint.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'rt_lint'`.

- [ ] **Step 3: Write `scripts/rt_lint.py`**

```python
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
            problems.append(
                f"{where}: references unknown service {service_name!r}"
            )
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_rt_lint.py -v`
Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/rt_lint.py tests/test_rt_lint.py
git commit -m "feat: lint template cross-service references and secret alphabets

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: The Aptabase template definition

**Files:**
- Create: `templates/aptabase/template.json`
- Test: `tests/test_aptabase_template.py`

**Interfaces:**
- Consumes: `rt_schema.load_template`, `rt_lint.lint_template`
- Produces: `templates/aptabase/template.json` — the definition every later task reads

Note the repo source `owner/name` below is `jorgeferrarice/railway`. If Task 12 pushes to a different GitHub owner or repository name, this value and the test asserting it must change together.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_aptabase_template.py`:

```python
from pathlib import Path

import pytest

import rt_lint
import rt_schema

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "aptabase" / "template.json"

APTABASE_DIGEST = "sha256:8efa3c0b451947c296410855666fb4ec8e812ddd15e4f236984284a6ad8510fe"


@pytest.fixture(scope="module")
def template():
    return rt_schema.load_template(TEMPLATE_PATH)


@pytest.fixture(scope="module")
def services(template):
    return {service["name"]: service for service in template["services"]}


def test_the_template_validates_against_the_schema(template):
    assert template["name"] == "Aptabase"


def test_the_template_lints_clean(template):
    assert rt_lint.lint_template(template) == []


def test_it_defines_exactly_the_three_expected_services(services):
    assert set(services) == {"postgres", "clickhouse", "aptabase"}


def test_the_app_image_is_pinned_to_the_expected_digest(services):
    image = services["aptabase"]["source"]["image"]
    assert image == f"ghcr.io/aptabase/aptabase@{APTABASE_DIGEST}"


def test_postgres_uses_the_railway_ssl_image_on_15(services):
    assert (
        services["postgres"]["source"]["image"]
        == "ghcr.io/railwayapp-templates/postgres-ssl:15.19"
    )


def test_clickhouse_builds_from_this_repository(services):
    source = services["clickhouse"]["source"]
    assert source["type"] == "repo"
    assert source["repo"] == "jorgeferrarice/railway"
    assert source["rootDirectory"] == "templates/aptabase/clickhouse"


def test_both_databases_have_a_volume(services):
    assert services["postgres"]["volumes"] == [{"mountPath": "/var/lib/postgresql/data"}]
    assert services["clickhouse"]["volumes"] == [{"mountPath": "/var/lib/clickhouse"}]


def test_the_app_has_no_volume(services):
    assert "volumes" not in services["aptabase"]


def test_only_the_app_is_publicly_reachable(services):
    assert services["aptabase"]["networking"]["http"]["targetPort"] == 8080
    assert "networking" not in services["postgres"]
    assert "networking" not in services["clickhouse"]


def test_the_health_check_tolerates_startup_migrations(services):
    deploy = services["aptabase"]["deploy"]
    assert deploy["healthcheckPath"] == "/healthz"
    assert deploy["healthcheckTimeout"] >= 300


def test_the_base_url_follows_the_generated_domain(services):
    value = services["aptabase"]["variables"]["BASE_URL"]["value"]
    assert value == "https://${{RAILWAY_PUBLIC_DOMAIN}}"


def test_the_postgres_connection_string_targets_the_private_domain(services):
    value = services["aptabase"]["variables"]["DATABASE_URL"]["value"]
    assert "${{postgres.RAILWAY_PRIVATE_DOMAIN}}" in value
    assert "Database=aptabase" in value
    assert "${{postgres.POSTGRES_PASSWORD}}" in value


def test_the_clickhouse_connection_string_omits_a_database(services):
    value = services["aptabase"]["variables"]["CLICKHOUSE_URL"]["value"]
    assert "${{clickhouse.RAILWAY_PRIVATE_DOMAIN}}" in value
    assert "Port=8123" in value
    assert "Database=" not in value


def test_clickhouse_does_not_set_a_default_database(services):
    assert "CLICKHOUSE_DB" not in services["clickhouse"]["variables"]


def test_the_app_port_is_pinned_to_match_the_declared_target_port(services):
    assert services["aptabase"]["variables"]["ASPNETCORE_HTTP_PORTS"]["value"] == "8080"


def test_the_region_is_self_hosted(services):
    assert services["aptabase"]["variables"]["REGION"]["value"] == "SH"


def test_smtp_and_oauth_variables_are_present_optional_and_empty(services):
    variables = services["aptabase"]["variables"]
    optional = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM_ADDRESS",
        "OAUTH_GITHUB_CLIENT_ID",
        "OAUTH_GITHUB_CLIENT_SECRET",
        "OAUTH_GOOGLE_CLIENT_ID",
        "OAUTH_GOOGLE_CLIENT_SECRET",
    ]
    for name in optional:
        assert variables[name]["value"] == ""
        assert variables[name]["isOptional"] is True


def test_generated_secrets_use_the_alphanumeric_alphabet(services):
    for service in services.values():
        for variable in service["variables"].values():
            if "secret(" in variable["value"]:
                assert rt_lint.SECRET_ALPHABET in variable["value"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_aptabase_template.py -v`
Expected: every test errors during fixture setup with `FileNotFoundError` for `templates/aptabase/template.json`.

- [ ] **Step 3: Write `templates/aptabase/template.json`**

The `${{secret(...)}}` alphabet below is one long literal string; do not wrap it.

```json
{
  "name": "Aptabase",
  "description": "Open-source, privacy-friendly analytics for mobile, desktop and web apps. Self-hosted, with PostgreSQL for accounts and ClickHouse for events.",
  "category": "Analytics",
  "readme": "templates/aptabase/README.md",
  "links": [
    {"label": "Source", "url": "https://github.com/aptabase/aptabase"},
    {"label": "Self-hosting guide", "url": "https://github.com/aptabase/self-hosting"},
    {"label": "Documentation", "url": "https://aptabase.com/docs"}
  ],
  "services": [
    {
      "name": "postgres",
      "source": {
        "type": "image",
        "image": "ghcr.io/railwayapp-templates/postgres-ssl:15.19"
      },
      "variables": {
        "POSTGRES_USER": {
          "value": "aptabase",
          "description": "PostgreSQL role Aptabase connects as."
        },
        "POSTGRES_DB": {
          "value": "aptabase",
          "description": "Database Aptabase runs its migrations against."
        },
        "POSTGRES_PASSWORD": {
          "value": "${{secret(32, \"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\")}}",
          "description": "Generated on deploy. Alphanumeric only, because it is interpolated into an ADO.NET connection string."
        },
        "PGDATA": {
          "value": "/var/lib/postgresql/data/pgdata",
          "description": "Data directory inside the mounted volume."
        }
      },
      "volumes": [{"mountPath": "/var/lib/postgresql/data"}],
      "deploy": {
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
      }
    },
    {
      "name": "clickhouse",
      "source": {
        "type": "repo",
        "repo": "jorgeferrarice/railway",
        "rootDirectory": "templates/aptabase/clickhouse",
        "branch": "main"
      },
      "variables": {
        "CLICKHOUSE_USER": {
          "value": "aptabase",
          "description": "ClickHouse user Aptabase connects as."
        },
        "CLICKHOUSE_PASSWORD": {
          "value": "${{secret(32, \"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\")}}",
          "description": "Generated on deploy. Alphanumeric only, because it is interpolated into an ADO.NET connection string."
        }
      },
      "volumes": [{"mountPath": "/var/lib/clickhouse"}],
      "deploy": {
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
      }
    },
    {
      "name": "aptabase",
      "source": {
        "type": "image",
        "image": "ghcr.io/aptabase/aptabase@sha256:8efa3c0b451947c296410855666fb4ec8e812ddd15e4f236984284a6ad8510fe"
      },
      "variables": {
        "BASE_URL": {
          "value": "https://${{RAILWAY_PUBLIC_DOMAIN}}",
          "description": "Public URL of this instance. Used to build activation and OAuth callback links."
        },
        "AUTH_SECRET": {
          "value": "${{secret(32, \"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\")}}",
          "description": "Signs auth tokens. Changing it signs every user out."
        },
        "DATABASE_URL": {
          "value": "Server=${{postgres.RAILWAY_PRIVATE_DOMAIN}};Port=5432;User Id=aptabase;Password=${{postgres.POSTGRES_PASSWORD}};Database=aptabase",
          "description": "PostgreSQL connection string, over the private network."
        },
        "CLICKHOUSE_URL": {
          "value": "Host=${{clickhouse.RAILWAY_PRIVATE_DOMAIN}};Port=8123;Username=aptabase;Password=${{clickhouse.CLICKHOUSE_PASSWORD}}",
          "description": "ClickHouse connection string, over the private network. No Database keyword, so events land in the default database, as upstream expects."
        },
        "ASPNETCORE_HTTP_PORTS": {
          "value": "8080",
          "description": "Pinned so the declared target port and Kestrel's listener cannot drift apart."
        },
        "REGION": {
          "value": "SH",
          "description": "Self-hosted."
        },
        "SMTP_HOST": {
          "value": "",
          "description": "Optional. Without SMTP, the signup activation link appears in this service's deploy logs instead of an inbox.",
          "isOptional": true
        },
        "SMTP_PORT": {"value": "", "description": "Optional SMTP port.", "isOptional": true},
        "SMTP_USERNAME": {"value": "", "description": "Optional SMTP username.", "isOptional": true},
        "SMTP_PASSWORD": {"value": "", "description": "Optional SMTP password.", "isOptional": true},
        "SMTP_FROM_ADDRESS": {"value": "", "description": "Optional sender address for outbound email.", "isOptional": true},
        "OAUTH_GITHUB_CLIENT_ID": {"value": "", "description": "Optional GitHub sign-in.", "isOptional": true},
        "OAUTH_GITHUB_CLIENT_SECRET": {"value": "", "description": "Optional GitHub sign-in.", "isOptional": true},
        "OAUTH_GOOGLE_CLIENT_ID": {"value": "", "description": "Optional Google sign-in.", "isOptional": true},
        "OAUTH_GOOGLE_CLIENT_SECRET": {"value": "", "description": "Optional Google sign-in.", "isOptional": true}
      },
      "networking": {"http": {"targetPort": 8080}},
      "deploy": {
        "healthcheckPath": "/healthz",
        "healthcheckTimeout": 300,
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
      }
    }
  ]
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_aptabase_template.py -v`
Expected: all 18 tests PASS.

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/pytest`
Expected: all tests from Tasks 2, 3 and 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add templates/aptabase/template.json tests/test_aptabase_template.py
git commit -m "feat: add the Aptabase template definition

Three services: Railway postgres-ssl 15.19, a ClickHouse image built from
this repo, and the Aptabase app pinned by digest.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: The ClickHouse service image

**Files:**
- Create: `templates/aptabase/clickhouse/Dockerfile`
- Create: `templates/aptabase/clickhouse/config.d/railway.xml`
- Create: `templates/aptabase/clickhouse/railway.json`
- Test: `tests/test_clickhouse_image.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces: a buildable Docker context at `templates/aptabase/clickhouse` that Railway builds as the `clickhouse` service

The tests build the image and run it. They are slow and require a running Docker daemon, so they are marked `docker` and skipped when Docker is unavailable.

- [ ] **Step 1: Register the `docker` marker**

Modify `pyproject.toml`, adding to the existing `[tool.pytest.ini_options]` table:

```toml
markers = ["docker: requires a running Docker daemon"]
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_clickhouse_image.py`:

```python
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import pytest

CONTEXT = Path(__file__).resolve().parent.parent / "templates" / "aptabase" / "clickhouse"
IMAGE_TAG = "railway-templates/aptabase-clickhouse:test"
USER = "aptabase"
PASSWORD = "testpassword"


def docker_available():
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not docker_available(), reason="Docker daemon is not running"),
]


def query(port, sql, timeout=2):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/?query={urllib.parse.quote(sql)}",
        headers={"X-ClickHouse-User": USER, "X-ClickHouse-Key": PASSWORD},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode().strip()


@pytest.fixture(scope="module")
def running_clickhouse():
    subprocess.run(["docker", "build", "-t", IMAGE_TAG, str(CONTEXT)], check=True)
    name = f"clickhouse-test-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        [
            "docker", "run", "-d", "--rm", "--name", name,
            "-p", "0:8123",
            "-e", f"CLICKHOUSE_USER={USER}",
            "-e", f"CLICKHOUSE_PASSWORD={PASSWORD}",
            IMAGE_TAG,
        ],
        check=True,
        capture_output=True,
    )
    try:
        port = subprocess.run(
            ["docker", "port", name, "8123/tcp"],
            check=True, capture_output=True, text=True,
        ).stdout.strip().rsplit(":", 1)[1]
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                if query(port, "SELECT 1") == "1":
                    break
            except (urllib.error.URLError, OSError):
                time.sleep(2)
        else:
            pytest.fail("ClickHouse did not become ready within 120s")
        yield port, name
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def test_it_answers_queries_for_the_configured_user(running_clickhouse):
    port, _ = running_clickhouse
    assert query(port, "SELECT 1") == "1"


def test_it_listens_on_ipv6(running_clickhouse):
    port, name = running_clickhouse
    result = subprocess.run(
        ["docker", "exec", name, "clickhouse-client",
         "--user", USER, "--password", PASSWORD,
         "--query", "SELECT value FROM system.server_settings WHERE name = 'listen_host'"],
        check=True, capture_output=True, text=True,
    )
    assert "::" in result.stdout


def test_memory_is_sized_from_the_container_limit(running_clickhouse):
    port, _ = running_clickhouse
    value = query(
        port,
        "SELECT value FROM system.server_settings WHERE name = 'max_server_memory_usage_to_ram_ratio'",
    )
    assert float(value) == pytest.approx(0.7)


def test_the_verbose_system_log_tables_are_disabled(running_clickhouse):
    port, _ = running_clickhouse
    query(port, "SELECT 1")
    time.sleep(10)
    existing = query(
        port,
        "SELECT name FROM system.tables WHERE database = 'system' "
        "AND name IN ('trace_log', 'metric_log', 'asynchronous_metric_log', 'text_log') "
        "ORDER BY name",
    )
    assert existing == ""


def test_the_railway_config_is_the_only_file_added(running_clickhouse):
    _, name = running_clickhouse
    result = subprocess.run(
        ["docker", "exec", name, "ls", "/etc/clickhouse-server/config.d/"],
        check=True, capture_output=True, text=True,
    )
    assert "railway.xml" in result.stdout


def test_the_railway_json_declares_a_dockerfile_build():
    config = json.loads((CONTEXT / "railway.json").read_text())
    assert config["build"]["builder"] == "DOCKERFILE"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_clickhouse_image.py -v`
Expected: the module-scoped fixture fails on `docker build` because `templates/aptabase/clickhouse/Dockerfile` does not exist, and `test_the_railway_json_declares_a_dockerfile_build` fails with `FileNotFoundError`.

- [ ] **Step 4: Write `templates/aptabase/clickhouse/config.d/railway.xml`**

```xml
<clickhouse>
    <!--
        Railway-specific tuning for the Aptabase events database.

        Not set here: listen_host. The upstream image already ships
        config.d/docker_related_config.xml, which binds "::" and so satisfies
        Railway's IPv6-only private networking.
    -->

    <logger>
        <level>warning</level>
        <console>1</console>
    </logger>

    <!-- Size caches from the container's memory limit, not the host's RAM. -->
    <max_server_memory_usage_to_ram_ratio>0.7</max_server_memory_usage_to_ram_ratio>
    <mark_cache_size>268435456</mark_cache_size>

    <!--
        Railway volumes start at 5 GB. Stock ClickHouse system logs would claim
        a large share of that before a single analytics event arrives, so the
        high-volume tables are removed and the rest are given a short TTL.
    -->
    <trace_log remove="1"/>
    <metric_log remove="1"/>
    <asynchronous_metric_log remove="1"/>
    <session_log remove="1"/>
    <text_log remove="1"/>
    <crash_log remove="1"/>

    <query_log>
        <database>system</database>
        <table>query_log</table>
        <ttl>event_date + INTERVAL 7 DAY DELETE</ttl>
        <flush_interval_milliseconds>7500</flush_interval_milliseconds>
    </query_log>

    <part_log>
        <database>system</database>
        <table>part_log</table>
        <ttl>event_date + INTERVAL 7 DAY DELETE</ttl>
        <flush_interval_milliseconds>7500</flush_interval_milliseconds>
    </part_log>
</clickhouse>
```

- [ ] **Step 5: Write `templates/aptabase/clickhouse/Dockerfile`**

```dockerfile
# Pinned to the exact version Aptabase's own compose file uses, so the
# ClickHouse migrations run against a server upstream has tested.
FROM clickhouse/clickhouse-server:23.8.4.69-alpine

COPY config.d/railway.xml /etc/clickhouse-server/config.d/railway.xml
```

- [ ] **Step 6: Write `templates/aptabase/clickhouse/railway.json`**

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_clickhouse_image.py -v`
Expected: all 6 tests PASS. The first run pulls the ClickHouse base image and may take several minutes.

If `test_the_verbose_system_log_tables_are_disabled` fails because a table still exists, the `remove="1"` attribute did not take effect for that table in ClickHouse 23.8. Do not delete the assertion — replace the offending `<x remove="1"/>` with an explicit empty element (for example `<text_log></text_log>`), rebuild, and re-run.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml templates/aptabase/clickhouse tests/test_clickhouse_image.py
git commit -m "feat: add the tuned ClickHouse image for the Aptabase template

Caps memory from the container limit and disables the high-volume system
log tables, which would otherwise consume a 5 GB Railway volume.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: Image digest bumper

**Files:**
- Create: `scripts/bump_digest.py`
- Test: `tests/test_bump_digest.py`

**Interfaces:**
- Consumes: `rt_schema.load_template`
- Produces:
  - `bump_digest.resolve_digest(repository: str, tag: str, *, opener=None) -> str` — returns `"sha256:…"`
  - `bump_digest.current_image(template: dict, service: str) -> str`
  - `bump_digest.bump(template_path: Path, service: str, tag: str, *, opener=None) -> tuple[str, str]` — returns `(old_image, new_image)` and rewrites the file when they differ

`opener` is an optional callable taking a `urllib.request.Request` and returning a file-like response, so tests can inject a fake registry.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bump_digest.py`:

```python
import io
import json
from pathlib import Path

import pytest

import bump_digest

NEW_DIGEST = "sha256:" + "b" * 64
OLD_DIGEST = "sha256:" + "a" * 64


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def fake_registry(digest=NEW_DIGEST, calls=None):
    def opener(request):
        if calls is not None:
            calls.append(request)
        if "/token" in request.full_url:
            return FakeResponse(json.dumps({"token": "fake-token"}).encode())
        return FakeResponse(headers={"Docker-Content-Digest": digest})

    return opener


def template_file(tmp_path, image):
    path = tmp_path / "template.json"
    path.write_text(
        json.dumps(
            {
                "name": "Example",
                "description": "An example template.",
                "category": "Analytics",
                "services": [
                    {
                        "name": "app",
                        "source": {"type": "image", "image": image},
                        "variables": {},
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )
    return path


def test_resolve_digest_returns_the_registry_digest():
    assert bump_digest.resolve_digest("aptabase/aptabase", "main", opener=fake_registry()) == NEW_DIGEST


def test_resolve_digest_requests_a_manifest_list():
    calls = []
    bump_digest.resolve_digest("aptabase/aptabase", "main", opener=fake_registry(calls=calls))
    manifest_request = calls[-1]
    assert manifest_request.get_method() == "HEAD"
    assert "manifest.list" in manifest_request.headers["Accept"]
    assert manifest_request.full_url.endswith("/manifests/main")


def test_resolve_digest_authenticates_with_the_pull_token():
    calls = []
    bump_digest.resolve_digest("aptabase/aptabase", "main", opener=fake_registry(calls=calls))
    assert calls[-1].headers["Authorization"] == "Bearer fake-token"


def test_resolve_digest_raises_when_the_registry_returns_no_digest():
    def opener(request):
        if "/token" in request.full_url:
            return FakeResponse(json.dumps({"token": "fake-token"}).encode())
        return FakeResponse(headers={})

    with pytest.raises(bump_digest.DigestResolutionError):
        bump_digest.resolve_digest("aptabase/aptabase", "main", opener=opener)


def test_current_image_reads_the_named_service(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    template = json.loads(path.read_text())
    assert bump_digest.current_image(template, "app") == f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}"


def test_current_image_raises_for_an_unknown_service(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    template = json.loads(path.read_text())
    with pytest.raises(KeyError):
        bump_digest.current_image(template, "nope")


def test_bump_rewrites_the_digest_in_place(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    old, new = bump_digest.bump(path, "app", "main", opener=fake_registry())
    assert old == f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}"
    assert new == f"ghcr.io/aptabase/aptabase@{NEW_DIGEST}"
    assert new in path.read_text()
    assert OLD_DIGEST not in path.read_text()


def test_bump_is_a_no_op_when_the_digest_is_unchanged(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{NEW_DIGEST}")
    before = path.read_text()
    old, new = bump_digest.bump(path, "app", "main", opener=fake_registry())
    assert old == new
    assert path.read_text() == before


def test_bump_preserves_the_rest_of_the_file_byte_for_byte(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    before = path.read_text()
    bump_digest.bump(path, "app", "main", opener=fake_registry())
    after = path.read_text()
    assert after == before.replace(OLD_DIGEST, NEW_DIGEST)


def test_bump_rejects_a_service_that_is_not_digest_pinned(tmp_path):
    path = template_file(tmp_path, "ghcr.io/aptabase/aptabase:main")
    with pytest.raises(bump_digest.DigestResolutionError):
        bump_digest.bump(path, "app", "main", opener=fake_registry())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_bump_digest.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'bump_digest'`.

- [ ] **Step 3: Write `scripts/bump_digest.py`**

The file is rewritten by string replacement rather than by re-serialising the parsed JSON, so a bump produces a one-line diff and leaves formatting, key order and comments-as-descriptions untouched.

```python
"""Re-resolve a digest-pinned image to the current digest behind its tag."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

REGISTRY = "ghcr.io"
TOKEN_URL = "https://ghcr.io/token"
MANIFEST_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


class DigestResolutionError(RuntimeError):
    """Raised when a digest cannot be resolved or applied."""


class _HeadRequest(urllib.request.Request):
    def get_method(self) -> str:
        return "HEAD"


def _default_opener(request):
    return urllib.request.urlopen(request, timeout=30)


def resolve_digest(repository: str, tag: str, *, opener=None) -> str:
    """Return the current manifest digest for ghcr.io/<repository>:<tag>."""
    opener = opener or _default_opener

    scope = urllib.parse.quote(f"repository:{repository}:pull", safe="")
    token_request = urllib.request.Request(f"{TOKEN_URL}?scope={scope}&service={REGISTRY}")
    with opener(token_request) as response:
        token = json.loads(response.read().decode())["token"]

    manifest_request = _HeadRequest(
        f"https://{REGISTRY}/v2/{repository}/manifests/{tag}",
        headers={"Authorization": f"Bearer {token}", "Accept": MANIFEST_ACCEPT},
    )
    with opener(manifest_request) as response:
        digest = response.headers.get("Docker-Content-Digest")

    if not digest:
        raise DigestResolutionError(
            f"{REGISTRY}/{repository}:{tag} returned no Docker-Content-Digest header"
        )
    return digest


def current_image(template: dict, service: str) -> str:
    """Return the image reference of the named service."""
    for candidate in template["services"]:
        if candidate["name"] == service:
            return candidate["source"]["image"]
    raise KeyError(f"no service named {service!r} in this template")


def bump(template_path: Path, service: str, tag: str, *, opener=None) -> tuple[str, str]:
    """Re-resolve the service's digest and rewrite the template file in place.

    Returns (old_image, new_image). They are equal when nothing changed, and in
    that case the file is left untouched.
    """
    template_path = Path(template_path)
    template = json.loads(template_path.read_text())
    old_image = current_image(template, service)

    if "@sha256:" not in old_image:
        raise DigestResolutionError(
            f"service {service!r} is not digest-pinned: {old_image!r}"
        )

    reference, old_digest = old_image.split("@", 1)
    repository = reference.split("/", 1)[1]
    new_digest = resolve_digest(repository, tag, opener=opener)
    new_image = f"{reference}@{new_digest}"

    if new_digest != old_digest:
        # Replace the digest textually so the diff stays one line and the rest
        # of the file's formatting survives untouched.
        template_path.write_text(template_path.read_text().replace(old_digest, new_digest))

    return old_image, new_image
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_bump_digest.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/bump_digest.py tests/test_bump_digest.py
git commit -m "feat: re-resolve pinned image digests from the registry

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Railway GraphQL client and introspection

**Files:**
- Create: `scripts/rt_api.py`
- Test: `tests/test_rt_api.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `rt_api.API_URL: str`
  - `rt_api.RailwayAPIError(RuntimeError)`
  - `rt_api.MissingTokenError(RailwayAPIError)`
  - `rt_api.get_token(env: dict | None = None) -> str`
  - `rt_api.graphql(query: str, variables: dict | None = None, *, token: str | None = None, opener=None) -> dict` — returns the `data` object
  - `rt_api.describe_type(name: str, *, token=None, opener=None) -> dict`
  - `rt_api.find_mutations(substring: str, *, token=None, opener=None) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rt_api.py`:

```python
import io
import json

import pytest

import rt_api


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def fake_transport(payload, calls=None):
    def opener(request):
        if calls is not None:
            calls.append(request)
        return FakeResponse(json.dumps(payload).encode())

    return opener


def test_get_token_reads_the_environment_variable():
    assert rt_api.get_token({"RAILWAY_API_TOKEN": "tok"}) == "tok"


def test_get_token_raises_when_unset():
    with pytest.raises(rt_api.MissingTokenError):
        rt_api.get_token({})


def test_get_token_raises_when_blank():
    with pytest.raises(rt_api.MissingTokenError):
        rt_api.get_token({"RAILWAY_API_TOKEN": "   "})


def test_graphql_returns_the_data_object():
    opener = fake_transport({"data": {"me": {"id": "abc"}}})
    assert rt_api.graphql("query { me { id } }", token="tok", opener=opener) == {"me": {"id": "abc"}}


def test_graphql_posts_to_the_railway_endpoint_with_bearer_auth():
    calls = []
    opener = fake_transport({"data": {}}, calls=calls)
    rt_api.graphql("query { me { id } }", token="tok", opener=opener)
    request = calls[0]
    assert request.full_url == rt_api.API_URL
    assert request.get_method() == "POST"
    assert request.headers["Authorization"] == "Bearer tok"
    assert json.loads(request.data)["query"] == "query { me { id } }"


def test_graphql_sends_variables():
    calls = []
    opener = fake_transport({"data": {}}, calls=calls)
    rt_api.graphql("query($id: String!) { x(id: $id) }", {"id": "1"}, token="tok", opener=opener)
    assert json.loads(calls[0].data)["variables"] == {"id": "1"}


def test_graphql_raises_on_graphql_errors():
    opener = fake_transport({"errors": [{"message": "Not authorized"}]})
    with pytest.raises(rt_api.RailwayAPIError) as excinfo:
        rt_api.graphql("query { me { id } }", token="tok", opener=opener)
    assert "Not authorized" in str(excinfo.value)


def test_describe_type_returns_the_input_fields():
    payload = {
        "data": {
            "__type": {
                "name": "TemplateCreateInput",
                "inputFields": [
                    {"name": "name", "type": {"name": "String", "kind": "SCALAR", "ofType": None}}
                ],
            }
        }
    }
    result = rt_api.describe_type("TemplateCreateInput", token="tok", opener=fake_transport(payload))
    assert result["name"] == "TemplateCreateInput"
    assert result["inputFields"][0]["name"] == "name"


def test_describe_type_raises_for_an_unknown_type():
    with pytest.raises(rt_api.RailwayAPIError):
        rt_api.describe_type("Nope", token="tok", opener=fake_transport({"data": {"__type": None}}))


def test_find_mutations_filters_case_insensitively():
    payload = {
        "data": {
            "__type": {
                "fields": [
                    {"name": "templateCreate"},
                    {"name": "templateDeployV2"},
                    {"name": "serviceCreate"},
                ]
            }
        }
    }
    found = rt_api.find_mutations("template", token="tok", opener=fake_transport(payload))
    assert found == ["templateCreate", "templateDeployV2"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_rt_api.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'rt_api'`.

- [ ] **Step 3: Write `scripts/rt_api.py`**

```python
"""Minimal Railway GraphQL client.

The token comes from the RAILWAY_API_TOKEN environment variable and nowhere
else. The Railway CLI's stored credentials are deliberately never read.
"""

from __future__ import annotations

import json
import os
import urllib.request

API_URL = "https://backboard.railway.com/graphql/v2"

TYPE_QUERY = """
query DescribeType($name: String!) {
  __type(name: $name) {
    name
    kind
    inputFields {
      name
      description
      defaultValue
      type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
    }
  }
}
"""

MUTATION_LIST_QUERY = """
query { __type(name: "Mutation") { fields { name } } }
"""


class RailwayAPIError(RuntimeError):
    """Raised when the Railway API returns errors or unexpected data."""


class MissingTokenError(RailwayAPIError):
    """Raised when RAILWAY_API_TOKEN is unset or blank."""


def get_token(env: dict | None = None) -> str:
    """Read the Railway API token from the environment."""
    token = (env if env is not None else os.environ).get("RAILWAY_API_TOKEN", "").strip()
    if not token:
        raise MissingTokenError(
            "RAILWAY_API_TOKEN is not set. Create a token at "
            "https://railway.com/account/tokens and export it."
        )
    return token


def _default_opener(request):
    return urllib.request.urlopen(request, timeout=60)


def graphql(query: str, variables: dict | None = None, *, token: str | None = None, opener=None) -> dict:
    """Execute a GraphQL document and return its data object."""
    opener = opener or _default_opener
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token or get_token()}",
        },
        method="POST",
    )
    with opener(request) as response:
        payload = json.loads(response.read().decode())

    if payload.get("errors"):
        messages = "; ".join(error.get("message", str(error)) for error in payload["errors"])
        raise RailwayAPIError(messages)
    return payload.get("data") or {}


def describe_type(name: str, *, token=None, opener=None) -> dict:
    """Return the introspected definition of a GraphQL type."""
    data = graphql(TYPE_QUERY, {"name": name}, token=token, opener=opener)
    type_definition = data.get("__type")
    if type_definition is None:
        raise RailwayAPIError(f"the Railway schema has no type named {name!r}")
    return type_definition


def find_mutations(substring: str, *, token=None, opener=None) -> list[str]:
    """Return every mutation name containing substring, case-insensitively."""
    data = graphql(MUTATION_LIST_QUERY, token=token, opener=opener)
    fields = (data.get("__type") or {}).get("fields") or []
    needle = substring.lower()
    return [field["name"] for field in fields if needle in field["name"].lower()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_rt_api.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/rt_api.py tests/test_rt_api.py
git commit -m "feat: add a Railway GraphQL client with schema introspection

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: Record the real template API schema

**Files:**
- Create: `scripts/railway_template.py` (first version: `validate`, `lint`, `introspect`, `bump`)
- Create: `docs/railway-template-api.md`

**Interfaces:**
- Consumes: `rt_schema`, `rt_lint`, `rt_api`, `bump_digest`
- Produces: `docs/railway-template-api.md` — the recorded input types that Task 9 writes its payload builder against

**This task requires a Railway API token.** `templateCreate` is not part of Railway's documented public API; its input shape must be read from the live schema rather than guessed. Ask the user to create a token at <https://railway.com/account/tokens> and export it as `RAILWAY_API_TOKEN` before starting. Do not read `~/.railway/config.json`.

- [ ] **Step 1: Write `scripts/railway_template.py`**

```python
#!/usr/bin/env python3
"""Manage Railway templates from version-controlled definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bump_digest
import rt_api
import rt_lint
import rt_schema


def cmd_validate(args) -> int:
    """Schema-validate a template definition."""
    try:
        rt_schema.load_template(Path(args.template))
    except rt_schema.TemplateValidationError as error:
        for problem in error.errors:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    print(f"{args.template}: valid")
    return 0


def cmd_lint(args) -> int:
    """Check cross-service references and repository invariants."""
    template = rt_schema.load_template(Path(args.template))
    problems = rt_lint.lint_template(template)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"{args.template}: clean")
    return 0


def cmd_introspect(args) -> int:
    """Print the GraphQL types needed to build template payloads."""
    if args.mutations:
        for name in rt_api.find_mutations(args.mutations):
            print(name)
        return 0
    for name in args.types:
        print(json.dumps(rt_api.describe_type(name), indent=2))
    return 0


def cmd_bump(args) -> int:
    """Re-resolve a digest-pinned image and rewrite the template."""
    old, new = bump_digest.bump(Path(args.template), args.service, args.tag)
    if old == new:
        print(f"{args.service}: already current ({new})")
    else:
        print(f"{args.service}: {old}\n{' ' * (len(args.service) + 2)}-> {new}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="railway_template", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="schema-validate a template definition")
    validate.add_argument("template")
    validate.set_defaults(func=cmd_validate)

    lint = subparsers.add_parser("lint", help="check references and invariants")
    lint.add_argument("template")
    lint.set_defaults(func=cmd_lint)

    introspect = subparsers.add_parser("introspect", help="read the Railway GraphQL schema")
    introspect.add_argument("types", nargs="*", help="type names to describe")
    introspect.add_argument("--mutations", help="list mutation names containing this substring")
    introspect.set_defaults(func=cmd_introspect)

    bump = subparsers.add_parser("bump", help="re-resolve a pinned image digest")
    bump.add_argument("template")
    bump.add_argument("--service", required=True)
    bump.add_argument("--tag", default="main")
    bump.set_defaults(func=cmd_bump)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (rt_api.RailwayAPIError, bump_digest.DigestResolutionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify the offline subcommands work**

```bash
.venv/bin/python scripts/railway_template.py validate templates/aptabase/template.json
.venv/bin/python scripts/railway_template.py lint templates/aptabase/template.json
```

Expected: `templates/aptabase/template.json: valid` then `templates/aptabase/template.json: clean`, exit code 0 for both.

- [ ] **Step 3: List the template mutations**

```bash
.venv/bin/python scripts/railway_template.py introspect --mutations template
```

Expected: a list of mutation names. `templateCreate`, `templateDeployV2` and a publish mutation are the ones of interest. Record the exact names printed.

- [ ] **Step 4: Describe the input types**

Run `introspect` on each type the mutations from Step 3 take. Start with the names Step 3 revealed, then follow every nested input type until no unexplored ones remain:

```bash
.venv/bin/python scripts/railway_template.py introspect TemplateCreateInput
```

Expected: JSON describing `inputFields`. Follow each field whose type is another `INPUT_OBJECT`.

- [ ] **Step 5: Write `docs/railway-template-api.md`**

Record, in prose and tables:

- The exact mutation names for create, update, publish and deploy, with their argument names and types.
- Every input type reached from those mutations: field names, types, whether required, and default values.
- How a service source (Docker image vs GitHub repo + root directory) is expressed.
- How variables, volumes, public networking and health checks are expressed.
- The date the schema was read, and a note that it is undocumented and may change.

- [ ] **Step 6: Commit**

```bash
git add scripts/railway_template.py docs/railway-template-api.md
git commit -m "feat: add the template CLI and record the Railway template API schema

templateCreate is undocumented, so its input types are read from the live
schema and recorded rather than guessed.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: Payload builder

**Files:**
- Create: `scripts/rt_payload.py`
- Test: `tests/test_rt_payload.py`

**Interfaces:**
- Consumes: `docs/railway-template-api.md` from Task 8 — the field names below come from that document, not from guesswork
- Produces:
  - `rt_payload.build_create_input(template: dict) -> dict`
  - `rt_payload.build_serialized_config(template: dict) -> dict`

Write the tests first, using the exact field names recorded in `docs/railway-template-api.md`. The assertions below name the *properties* the payload must have; substitute the real Railway field names for the placeholders marked `<…>` as you write them. Do not weaken an assertion to make a test pass — if the recorded schema contradicts one, the design is wrong and needs revisiting.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rt_payload.py` covering, at minimum:

- `build_create_input` carries the template `name`, `description` and `category` through to the recorded fields.
- Every service in `template.json` appears exactly once in the payload, keyed or named by its service name.
- An `image` source produces the recorded Docker-image source field with the full reference including `@sha256:`.
- A `repo` source produces the recorded repository field, the root directory field, and the branch.
- Variables become the recorded variable structure, with `description` and `isOptional` preserved.
- A variable whose value is `""` stays `""` and is not dropped.
- `volumes` produce the recorded volume structure with the correct mount path.
- The `aptabase` service's `networking.http.targetPort` produces the recorded public-networking structure on port 8080, and `postgres` and `clickhouse` produce none.
- `deploy.healthcheckPath`, `healthcheckTimeout`, `restartPolicyType` and `restartPolicyMaxRetries` map to the recorded deploy fields.
- `build_create_input(load_template("templates/aptabase/template.json"))` succeeds and round-trips through `json.dumps` without error.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_rt_payload.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'rt_payload'`.

- [ ] **Step 3: Write `scripts/rt_payload.py`**

Implement the two functions against the recorded schema. Structure the module as one small mapping function per concern — `_source`, `_variables`, `_volumes`, `_networking`, `_deploy` — each taking a service dict and returning the recorded fragment, and a `build_create_input` that assembles them. Keep the recorded field names in one module-level mapping constant so a schema change is a single-place edit.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_rt_payload.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/pytest`
Expected: every test from Tasks 2 through 9 PASSES.

- [ ] **Step 6: Commit**

```bash
git add scripts/rt_payload.py tests/test_rt_payload.py
git commit -m "feat: build Railway template API payloads from template.json

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: Create, update, publish and deploy subcommands

**Files:**
- Modify: `scripts/railway_template.py`
- Test: `tests/test_railway_template_cli.py`

**Interfaces:**
- Consumes: `rt_payload.build_create_input`, `rt_api.graphql`
- Produces: `railway_template.main(argv: list[str] | None = None) -> int` handling `create`, `update`, `publish` and `deploy`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_railway_template_cli.py`. Every test injects a fake `rt_api.graphql` via monkeypatch, so no test reaches the network:

```python
import json

import pytest

import railway_template
import rt_api


@pytest.fixture
def recorded(monkeypatch):
    calls = []

    def fake_graphql(query, variables=None, **kwargs):
        calls.append((query, variables))
        if "templateCreate" in query:
            return {"templateCreate": {"id": "tpl_123", "code": "aptabase"}}
        if "templateUpdate" in query:
            return {"templateUpdate": {"id": "tpl_123"}}
        if "templatePublish" in query:
            return {"templatePublish": {"id": "tpl_123"}}
        return {"templateDeployV2": {"projectId": "prj_123", "workflowId": "wf_1"}}

    monkeypatch.setattr(railway_template.rt_api, "graphql", fake_graphql)
    return calls


TEMPLATE = "templates/aptabase/template.json"


def test_create_sends_the_built_payload(recorded, capsys):
    assert railway_template.main(["create", TEMPLATE]) == 0
    _, variables = recorded[0]
    assert variables["input"]["name"] == "Aptabase"
    assert "tpl_123" in capsys.readouterr().out


def test_create_refuses_a_template_that_fails_lint(tmp_path, monkeypatch, capsys):
    broken = tmp_path / "template.json"
    broken.write_text(json.dumps({
        "name": "Broken",
        "description": "d",
        "category": "Analytics",
        "services": [{
            "name": "app",
            "source": {"type": "image", "image": "ghcr.io/aptabase/aptabase:main"},
            "variables": {},
        }],
    }))
    assert railway_template.main(["create", str(broken)]) == 1
    assert "digest" in capsys.readouterr().err


def test_update_requires_a_template_id(recorded):
    with pytest.raises(SystemExit):
        railway_template.main(["update", TEMPLATE])


def test_update_sends_the_template_id(recorded):
    assert railway_template.main(["update", TEMPLATE, "--template-id", "tpl_123"]) == 0
    _, variables = recorded[0]
    assert variables["id"] == "tpl_123"


def test_publish_requires_a_template_id(recorded):
    with pytest.raises(SystemExit):
        railway_template.main(["publish"])


def test_deploy_requires_a_project_id(recorded):
    with pytest.raises(SystemExit):
        railway_template.main(["deploy", TEMPLATE])


def test_deploy_sends_the_project_id(recorded, capsys):
    assert railway_template.main(["deploy", TEMPLATE, "--project-id", "prj_123"]) == 0
    _, variables = recorded[0]
    assert variables["input"]["projectId"] == "prj_123"


def test_api_errors_become_exit_code_one(monkeypatch, capsys):
    def failing(*args, **kwargs):
        raise rt_api.RailwayAPIError("Not authorized")

    monkeypatch.setattr(railway_template.rt_api, "graphql", failing)
    assert railway_template.main(["create", TEMPLATE]) == 1
    assert "Not authorized" in capsys.readouterr().err


def test_a_missing_token_is_reported_clearly(monkeypatch, capsys):
    monkeypatch.delenv("RAILWAY_API_TOKEN", raising=False)
    assert railway_template.main(["create", TEMPLATE]) == 1
    assert "RAILWAY_API_TOKEN" in capsys.readouterr().err
```

Adjust the mutation names and variable keys in the fake to match `docs/railway-template-api.md`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_railway_template_cli.py -v`
Expected: failures with `AttributeError` or `SystemExit: 2` — `create`, `update`, `publish` and `deploy` are not registered subcommands yet.

- [ ] **Step 3: Add the subcommands to `scripts/railway_template.py`**

Add `cmd_create`, `cmd_update`, `cmd_publish` and `cmd_deploy`, plus their subparsers. Each of `create`, `update` and `deploy` must lint the template first and return `1` without touching the network when `rt_lint.lint_template` reports problems — an invalid template should never reach Railway. Extend the `except` clause in `main` to cover `rt_api.MissingTokenError` (already a `RailwayAPIError` subclass, so it is covered; confirm the message reaches stderr).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_railway_template_cli.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/pytest`
Expected: everything PASSES.

- [ ] **Step 6: Commit**

```bash
git add scripts/railway_template.py tests/test_railway_template_cli.py
git commit -m "feat: add create, update, publish and deploy subcommands

Every network-touching subcommand lints the template first, so a broken
definition never reaches Railway.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 11: Template README and marketplace listing

**Files:**
- Create: `templates/aptabase/README.md`

**Interfaces:**
- Consumes: `templates/aptabase/template.json`
- Produces: the listing copy referenced by `template.json`'s `readme` field

- [ ] **Step 1: Write `templates/aptabase/README.md`**

It must cover, each as its own section:

1. **What this deploys** — Aptabase, three services, one sentence each, and the note that this instance runs `REGION=SH` and sends no data anywhere.
2. **Deploy** — the template URL once it exists, and the `railway_template.py deploy` command as the scripted alternative.
3. **First account** — the section that matters most. Aptabase ships no default credentials. Register through the UI, then: with no SMTP configured, the activation email is never sent and the activation link is printed in the `aptabase` service's deploy logs. Give the exact path: Railway project → `aptabase` service → Deployments → the active deployment → View logs → search for the activation URL. State plainly that this is expected, not a broken deploy.
4. **Adding SMTP** — the five `SMTP_*` variables, that all five are needed, and that the service restarts on change.
5. **Adding OAuth** — the four `OAUTH_*` variables and that the callback URL derives from `BASE_URL`.
6. **Custom domain** — add the domain in Railway, then update `BASE_URL` to match, because activation and OAuth callback links are built from it. Getting this wrong produces links pointing at the old domain.
7. **Upgrading** — `railway_template.py bump templates/aptabase/template.json --service aptabase --tag main`, review the one-line diff, commit, then `update`. Note that upstream publishes no version tags, so a bump is a jump to whatever `main` currently is; read upstream's commits before bumping.
8. **Storage** — both databases have volumes; ClickHouse system logs are disabled and TTL'd to protect the 5 GB default; how to grow a volume in Railway.
9. **Known limits** — ClickHouse 23.8 under Railway's memory limits is not something upstream tests; the health check allows 300 s because migrations run before the server binds, so first deploys are slow.
10. **Marketplace listing** — name `Aptabase`, category `Analytics`, the short description from `template.json`, and the three links. A note that icon and banner assets are supplied through the Railway template editor and that Aptabase's trademarks are not vendored here.

- [ ] **Step 2: Verify the README path in `template.json` resolves**

```bash
.venv/bin/python -c "
import json, pathlib
template = json.loads(pathlib.Path('templates/aptabase/template.json').read_text())
assert pathlib.Path(template['readme']).exists(), template['readme']
print('readme path resolves')
"
```

Expected: `readme path resolves`.

- [ ] **Step 3: Commit**

```bash
git add templates/aptabase/README.md
git commit -m "docs: add the Aptabase template guide and marketplace listing

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 12: Push the repository to GitHub

**Files:** none

**Interfaces:**
- Consumes: everything committed so far
- Produces: a GitHub repository Railway can build the ClickHouse service from

**GATE: outward-facing. Run only on explicit instruction from the user.** Publishing this repository puts it on GitHub, where it may be cached or indexed. Confirm the repository name and visibility before creating anything.

- [ ] **Step 1: Confirm the destination with the user**

Ask for the repository owner, name and visibility. `templates/aptabase/template.json` currently declares `jorgeferrarice/railway`. If the answer differs, update `template.json` and the assertion in `tests/test_aptabase_template.py::test_clickhouse_builds_from_this_repository` together, run `.venv/bin/pytest`, and commit before pushing.

- [ ] **Step 2: Create the repository and push**

```bash
gh repo create <owner>/<name> --<visibility> --source=. --remote=origin --push
```

Expected: the repository exists and `main` is pushed.

- [ ] **Step 3: Verify Railway can see the build context**

Confirm `templates/aptabase/clickhouse/Dockerfile` is present in the pushed tree on GitHub. Railway builds from that path; if it is missing, the `clickhouse` service cannot deploy.

---

## Task 13: End-to-end deploy verification

**Files:** none

**Interfaces:**
- Consumes: the pushed repository and the working CLI
- Produces: the evidence for acceptance criteria 3 through 5 in the spec

**GATE: outward-facing and billable. Run only on explicit instruction from the user.**

- [ ] **Step 1: Create the template**

```bash
.venv/bin/python scripts/railway_template.py create templates/aptabase/template.json
```

Expected: a template id and code are printed. Record them.

- [ ] **Step 2: Verify the template in the Railway editor**

Open the template in Railway's template editor. Confirm, service by service: three services named `postgres`, `clickhouse`, `aptabase`; the variables from `template.json`; volumes on both databases and none on the app; a public HTTP domain on `aptabase` only, target port 8080; health check `/healthz` with a 300 second timeout.

- [ ] **Step 3: Deploy into a scratch project**

```bash
.venv/bin/python scripts/railway_template.py deploy templates/aptabase/template.json --project-id <project id>
```

Expected: the deploy starts. Watch all three services.

- [ ] **Step 4: Verify the instance is reachable**

Open the generated public domain. Expected: the Aptabase signup page renders over HTTPS.

If the `aptabase` service is unhealthy, check in this order: its deploy logs for a migration error; that `DATABASE_URL` and `CLICKHOUSE_URL` resolved their references rather than containing literal `${{…}}`; that both databases are running.

- [ ] **Step 5: Verify the first-account flow**

Register an account through the UI. Find the activation link in the `aptabase` service's deploy logs. Complete activation.
Expected: the Aptabase dashboard loads. This is acceptance criterion 5 and the single most likely thing to confuse a template user, so confirm the README's instructions match what actually appears in the logs — and fix the README if they do not.

- [ ] **Step 6: Verify event ingestion end to end**

Create an app in the Aptabase UI, take its app key, and send a test event with the documented ingest endpoint. Confirm it appears in the dashboard.
Expected: the event is visible, which proves the ClickHouse connection and its migrations work.

- [ ] **Step 7: Publish to the marketplace**

```bash
.venv/bin/python scripts/railway_template.py publish --template-id <template id>
```

Expected: the template appears on the marketplace. Add icon and banner assets through the Railway template editor.

- [ ] **Step 8: Tear down the scratch project**

Delete the verification project in Railway so it stops accruing cost.

---

## Task 14: Knowledge graph and final baseline check

**Files:**
- Create: `graphify-out/graph.json` and its companion outputs

**Interfaces:**
- Consumes: the finished repository
- Produces: a repository that satisfies all three baseline requirements

- [ ] **Step 1: Build the knowledge graph**

Run the `/graphify .` slash command in this repository.
Expected: `graphify-out/graph.json` exists along with the HTML and audit report.

- [ ] **Step 2: Verify the full baseline**

```bash
ls AGENTS.md .cursor/rules/caveman.mdc .windsurf/rules/caveman.md .clinerules/caveman.md .opencode/AGENTS.md .github/copilot-instructions.md RTK.md graphify-out/graph.json
command -v rtk
```

Expected: every path listed with no `No such file` error, and `rtk` resolves on PATH.

- [ ] **Step 3: Run the whole suite one final time**

```bash
.venv/bin/pytest
```

Expected: every test passes. Report the actual count; do not claim success without reading the output.

- [ ] **Step 4: Commit**

```bash
git add graphify-out
git commit -m "chore: build the repository knowledge graph

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: repository layout → Task 1; service design → Tasks 4 and 5; `template.json` → Task 4; `scripts/railway_template.py` subcommands → Tasks 8 and 10; `bump-digest` → Task 6; marketplace listing → Tasks 11 and 13 Step 7; post-deploy activation-link behaviour → Task 11 Section 3 and Task 13 Step 5; error handling table → covered by the ClickHouse config (Task 5), the secret alphabet lint (Task 3), the health check timeout (Task 4) and the README (Task 11); acceptance criteria 1–2 → Tasks 8 and 9; 3–6 → Task 13 and Task 6; 7 → Task 14.

**Placeholder scan.** Task 9's payload field names and Task 10's mutation names are deliberately deferred to `docs/railway-template-api.md`, produced by Task 8. This is a discovery dependency, not a placeholder: the spec records that the schema is undocumented and that no GraphQL is written from guesswork. Every other step carries its literal content. Task 11 specifies section-by-section content rather than finished prose, which is appropriate for a document whose exact wording depends on what Task 13 Step 5 observes.

**Type consistency.** `rt_schema.load_template` is used in Tasks 3, 4, 8 and 9 with the same signature. `rt_lint.lint_template` returns `list[str]` in Tasks 3, 8 and 10. `rt_api.graphql` returns the `data` object in Tasks 7, 9 and 10. `bump_digest.bump` returns `(old, new)` in Tasks 6 and 8. `rt_lint.SECRET_ALPHABET` is defined in Task 3 and asserted against in Task 4.
