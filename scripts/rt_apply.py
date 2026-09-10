"""Build a template's services directly in a Railway project.

Railway's `templateDeployV2` mutation is refused from the public API — it fails
with an opaque 400 for every input, including Railway's own published templates,
while ordinary mutations like `serviceCreate` succeed with the same token. See
docs/railway-template-api.md.

The supported route to a template is therefore Railway's documented "generate
from project" flow: build the services here, then `templateGenerate` against the
finished project.

Note that Railway expands template variable functions such as
`${{secret(32, "...")}}` when the variable is written, so the project ends up
with real generated secrets rather than the generator expression.
"""

from __future__ import annotations

import rt_api

SERVICE_CREATE = """
mutation CreateService($input: ServiceCreateInput!) {
  serviceCreate(input: $input) { id name }
}
"""

SERVICE_INSTANCE_UPDATE = """
mutation UpdateInstance($serviceId: String!, $environmentId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
}
"""

VARIABLES_UPSERT = """
mutation UpsertVariables($input: VariableCollectionUpsertInput!) {
  variableCollectionUpsert(input: $input)
}
"""

VOLUME_CREATE = """
mutation CreateVolume($input: VolumeCreateInput!) {
  volumeCreate(input: $input) { id }
}
"""

DOMAIN_CREATE = """
mutation CreateDomain($input: ServiceDomainCreateInput!) {
  serviceDomainCreate(input: $input) { domain }
}
"""

INSTANCE_SETTINGS = (
    "healthcheckPath",
    "healthcheckTimeout",
    "restartPolicyType",
    "restartPolicyMaxRetries",
    "startCommand",
)


def apply_template(
    template: dict,
    project_id: str,
    environment_id: str,
    *,
    graphql=rt_api.graphql,
) -> dict[str, str]:
    """Create every service in the template. Returns {service name: id}."""
    services = template["services"]

    # Create all services first. A variable such as ${{postgres.PASSWORD}}
    # cannot resolve until the service it names exists, so nothing is written
    # until every service is present.
    ids = {
        service["name"]: _create_service(graphql, service, project_id, environment_id)
        for service in services
    }

    for service in services:
        service_id = ids[service["name"]]
        _set_variables(graphql, service, service_id, project_id, environment_id)
        _update_instance(graphql, service, service_id, environment_id)
        _create_volumes(graphql, service, service_id, project_id, environment_id)
        _create_domain(graphql, service, service_id, environment_id)

    return ids


def _create_service(graphql, service: dict, project_id: str, environment_id: str) -> str:
    source = service["source"]
    payload = {
        "projectId": project_id,
        "environmentId": environment_id,
        "name": service["name"],
    }
    if source["type"] == "image":
        payload["source"] = {"image": source["image"]}
    else:
        payload["source"] = {"repo": source["repo"]}
        if source.get("branch"):
            payload["branch"] = source["branch"]
    return graphql(SERVICE_CREATE, {"input": payload})["serviceCreate"]["id"]


def _set_variables(graphql, service: dict, service_id, project_id, environment_id) -> None:
    variables = {
        name: variable["value"] for name, variable in (service.get("variables") or {}).items()
    }
    if not variables:
        return
    graphql(
        VARIABLES_UPSERT,
        {
            "input": {
                "projectId": project_id,
                "environmentId": environment_id,
                "serviceId": service_id,
                "variables": variables,
            }
        },
    )


def _update_instance(graphql, service: dict, service_id, environment_id) -> None:
    deploy = service.get("deploy") or {}
    payload = {key: deploy[key] for key in INSTANCE_SETTINGS if key in deploy}

    source = service["source"]
    if source["type"] == "repo":
        payload["rootDirectory"] = "/" + source["rootDirectory"].lstrip("/")

    if not payload:
        return
    graphql(
        SERVICE_INSTANCE_UPDATE,
        {"serviceId": service_id, "environmentId": environment_id, "input": payload},
    )


def _create_volumes(graphql, service: dict, service_id, project_id, environment_id) -> None:
    for volume in service.get("volumes") or []:
        graphql(
            VOLUME_CREATE,
            {
                "input": {
                    "projectId": project_id,
                    "environmentId": environment_id,
                    "serviceId": service_id,
                    "mountPath": volume["mountPath"],
                }
            },
        )


def _create_domain(graphql, service: dict, service_id, environment_id) -> None:
    http = (service.get("networking") or {}).get("http")
    if not http:
        return
    graphql(
        DOMAIN_CREATE,
        {
            "input": {
                "environmentId": environment_id,
                "serviceId": service_id,
                "targetPort": http["targetPort"],
            }
        },
    )
