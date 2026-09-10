"""Translate a template.json into Railway's serializedConfig payload.

SerializedTemplateConfig is a custom GraphQL scalar — an opaque JSON blob whose
shape cannot be introspected. Every field name below was reverse-engineered from
the serializedConfig of published Railway templates; see
docs/railway-template-api.md for the evidence and the date it was read.

Keeping the field names in one module means a schema change is a single-place
edit.
"""

from __future__ import annotations

import posixpath
import re
import uuid
from pathlib import Path

# Literal key Railway uses to mean "this service gets a generated domain". It is
# not a placeholder to substitute.
HAS_DOMAIN = "<hasDomain>"

# serializedConfig has no healthcheckTimeout field. Railway reads the timeout
# from this service variable instead, and a template can carry variables.
HEALTHCHECK_TIMEOUT_VARIABLE = "RAILWAY_HEALTHCHECK_TIMEOUT_SEC"

# Namespace for deriving stable service and volume ids. Railway keys services by
# UUID; deriving them from the template and service names rather than generating
# them fresh keeps a rebuilt payload identical to the last one.
ID_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def service_id(template_name: str, service_name: str) -> str:
    """Return the stable UUID for a service within a template."""
    return str(uuid.uuid5(ID_NAMESPACE, f"{template_name}/{service_name}"))


def volume_id(template_name: str, service_name: str, mount_path: str) -> str:
    """Return the stable UUID for a volume mounted on a service."""
    return str(uuid.uuid5(ID_NAMESPACE, f"{template_name}/{service_name}{mount_path}"))


def build_serialized_config(template: dict) -> dict:
    """Build the serializedConfig blob for a template definition."""
    template_name = template["name"]
    return {
        "services": {
            service_id(template_name, service["name"]): _service(template_name, service)
            for service in template["services"]
        }
    }


def _service(template_name: str, service: dict) -> dict:
    volumes = service.get("volumes") or []
    deploy = _deploy(service, volumes)
    return {
        # The name is what cross-service references resolve against, so it is
        # carried verbatim rather than prettified.
        "name": service["name"],
        "source": _source(service["source"]),
        "variables": _variables(service),
        "deploy": deploy,
        "networking": _networking(service),
        "volumeMounts": _volume_mounts(template_name, service, volumes),
    }


def _source(source: dict) -> dict:
    if source["type"] == "image":
        return {"image": source["image"]}
    return {
        "repo": source["repo"],
        # Railway writes this path with a leading slash.
        "rootDirectory": "/" + source["rootDirectory"].lstrip("/"),
        "branch": source.get("branch"),
    }


def _variables(service: dict) -> dict:
    variables = {
        name: {
            "defaultValue": variable["value"],
            "description": variable.get("description", ""),
            "isOptional": bool(variable.get("isOptional", False)),
        }
        for name, variable in (service.get("variables") or {}).items()
    }

    timeout = (service.get("deploy") or {}).get("healthcheckTimeout")
    if timeout is not None and HEALTHCHECK_TIMEOUT_VARIABLE not in variables:
        variables[HEALTHCHECK_TIMEOUT_VARIABLE] = {
            "defaultValue": str(timeout),
            "description": "Seconds Railway waits for the health check to pass.",
            "isOptional": False,
        }
    return variables


def _deploy(service: dict, volumes: list) -> dict:
    source = service.get("deploy") or {}
    deploy = {
        key: source[key]
        for key in ("healthcheckPath", "startCommand", "restartPolicyType", "restartPolicyMaxRetries")
        if key in source
    }
    if volumes:
        deploy["requiredMountPath"] = volumes[0]["mountPath"]
    return deploy


def _networking(service: dict) -> dict:
    http = (service.get("networking") or {}).get("http")
    if not http:
        return {}
    port = http["targetPort"]
    return {"serviceDomains": {f"{HAS_DOMAIN}:{port}": {"port": port}}}


def _volume_mounts(template_name: str, service: dict, volumes: list) -> dict:
    return {
        volume_id(template_name, service["name"], volume["mountPath"]): {
            "mountPath": volume["mountPath"]
        }
        for volume in volumes
    }


def build_deploy_input(
    template: dict,
    *,
    project_id: str | None = None,
    environment_id: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    """Build the TemplateDeployV2Input for this template."""
    targets = {
        "projectId": project_id,
        "environmentId": environment_id,
        "workspaceId": workspace_id,
    }
    payload = {key: value for key, value in targets.items() if value is not None}
    payload["serializedConfig"] = build_serialized_config(template)
    return payload


# Everything below this marker in a readme is for whoever maintains the
# template, not for whoever deploys it, so it does not go to the marketplace.
README_END_MARKER = "<!-- marketplace:end -->"

# Markdown link whose target is not already absolute, an anchor, or a scheme
# such as mailto:. Those are the ones the marketplace cannot resolve.
_RELATIVE_LINK = re.compile(r"\]\((?![a-z][a-z0-9+.-]*:|#|/)([^)\s]+)\)")


def absolute_links(readme: str, repository: str, readme_root: str) -> str:
    """Rewrite relative markdown links against the repository.

    The marketplace renders the readme on its own page, where a link like
    `clickhouse/config.d/railway.xml` points at nothing. `readme_root` is the
    readme's directory within the repository, so `../../docs/x.md` resolves the
    way it does on GitHub.
    """
    base = repository.rstrip("/") + "/blob/main"

    def rewrite(match: re.Match) -> str:
        target = posixpath.normpath(posixpath.join(readme_root, match.group(1)))
        return f"]({base}/{target})"

    return _RELATIVE_LINK.sub(rewrite, readme)


def build_publish_input(
    template: dict,
    *,
    workspace_id: str | None = None,
    readme_root: str | None = None,
) -> dict:
    """Build the TemplatePublishInput carrying the marketplace metadata."""
    payload = {
        "category": template["category"],
        "description": template["description"],
        "readme": _readme(template, readme_root),
    }
    if workspace_id is not None:
        payload["workspaceId"] = workspace_id
    return payload


def _readme(template: dict, readme_root: str | None) -> str | None:
    readme_path = template.get("readme")
    if not readme_path:
        return None

    readme = Path(readme_path).read_text()
    readme = readme.split(README_END_MARKER)[0].rstrip() if README_END_MARKER in readme else readme
    repository = template.get("repository")
    if repository:
        root = readme_root
        if root is None:
            root = str(Path(readme_path).parent)
        readme = absolute_links(readme, repository, root)

    links = template.get("links")
    if links:
        rows = "".join(f"- [{link['label']}]({link['url']})\n" for link in links)
        readme = f"{readme.rstrip()}\n\n## Links\n\n{rows}"
    return readme
