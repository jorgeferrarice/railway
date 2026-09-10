import json
import uuid
from pathlib import Path

import pytest

import rt_payload
import rt_schema

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "aptabase" / "template.json"


def template_with(services, name="Example"):
    return {
        "name": name,
        "description": "An example template.",
        "category": "Analytics",
        "services": services,
    }


def only_service(config):
    return next(iter(config["services"].values()))


def test_service_keys_are_uuids():
    config = rt_payload.build_serialized_config(
        template_with([{"name": "app", "source": {"type": "image", "image": "img:1"}}])
    )
    key = next(iter(config["services"]))
    assert uuid.UUID(key)


def test_service_ids_are_stable_across_runs():
    template = template_with([{"name": "app", "source": {"type": "image", "image": "img:1"}}])
    first = rt_payload.build_serialized_config(template)
    second = rt_payload.build_serialized_config(template)
    assert list(first["services"]) == list(second["services"])


def test_different_services_get_different_ids():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {"name": "app", "source": {"type": "image", "image": "img:1"}},
                {"name": "db", "source": {"type": "image", "image": "img:2"}},
            ]
        )
    )
    assert len(config["services"]) == 2


def test_the_service_name_is_carried_verbatim():
    """Cross-service references resolve by service name, so it must match
    exactly what ${{postgres.X}} in another variable spells.
    """
    config = rt_payload.build_serialized_config(
        template_with([{"name": "postgres", "source": {"type": "image", "image": "img:1"}}])
    )
    assert only_service(config)["name"] == "postgres"


def test_an_image_source_is_passed_through():
    config = rt_payload.build_serialized_config(
        template_with(
            [{"name": "app", "source": {"type": "image", "image": "ghcr.io/x/y@sha256:" + "a" * 64}}]
        )
    )
    assert only_service(config)["source"] == {"image": "ghcr.io/x/y@sha256:" + "a" * 64}


def test_a_repo_source_gets_a_leading_slash_on_the_root_directory():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {
                        "type": "repo",
                        "repo": "owner/name",
                        "rootDirectory": "templates/app",
                        "branch": "main",
                    },
                }
            ]
        )
    )
    assert only_service(config)["source"] == {
        "repo": "owner/name",
        "rootDirectory": "/templates/app",
        "branch": "main",
    }


def test_a_repo_source_without_a_branch_sends_null():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "repo", "repo": "owner/name", "rootDirectory": "app"},
                }
            ]
        )
    )
    assert only_service(config)["source"]["branch"] is None


def test_variables_use_default_value_not_value():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "image", "image": "img:1"},
                    "variables": {"A": {"value": "1", "description": "the a"}},
                }
            ]
        )
    )
    assert only_service(config)["variables"]["A"] == {
        "defaultValue": "1",
        "description": "the a",
        "isOptional": False,
    }


def test_an_optional_variable_is_marked_optional():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "image", "image": "img:1"},
                    "variables": {"A": {"value": "", "isOptional": True}},
                }
            ]
        )
    )
    variable = only_service(config)["variables"]["A"]
    assert variable["isOptional"] is True
    assert variable["defaultValue"] == ""


def test_a_volume_produces_both_a_mount_and_a_required_mount_path():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "db",
                    "source": {"type": "image", "image": "img:1"},
                    "volumes": [{"mountPath": "/var/lib/db"}],
                }
            ]
        )
    )
    service = only_service(config)
    assert service["deploy"]["requiredMountPath"] == "/var/lib/db"
    mount = next(iter(service["volumeMounts"].values()))
    assert mount == {"mountPath": "/var/lib/db"}
    assert uuid.UUID(next(iter(service["volumeMounts"])))


def test_a_service_without_a_volume_has_no_volume_mounts():
    config = rt_payload.build_serialized_config(
        template_with([{"name": "app", "source": {"type": "image", "image": "img:1"}}])
    )
    assert only_service(config)["volumeMounts"] == {}


def test_http_networking_uses_the_has_domain_key():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "image", "image": "img:1"},
                    "networking": {"http": {"targetPort": 8080}},
                }
            ]
        )
    )
    assert only_service(config)["networking"] == {
        "serviceDomains": {"<hasDomain>:8080": {"port": 8080}}
    }


def test_a_private_service_has_empty_networking():
    config = rt_payload.build_serialized_config(
        template_with([{"name": "db", "source": {"type": "image", "image": "img:1"}}])
    )
    assert only_service(config)["networking"] == {}


def test_deploy_carries_the_health_path_and_restart_policy():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "image", "image": "img:1"},
                    "deploy": {
                        "healthcheckPath": "/healthz",
                        "restartPolicyType": "ON_FAILURE",
                        "restartPolicyMaxRetries": 10,
                    },
                }
            ]
        )
    )
    deploy = only_service(config)["deploy"]
    assert deploy["healthcheckPath"] == "/healthz"
    assert deploy["restartPolicyType"] == "ON_FAILURE"
    assert deploy["restartPolicyMaxRetries"] == 10


def test_healthcheck_timeout_becomes_a_service_variable():
    """serializedConfig has no healthcheckTimeout field. Railway reads the
    timeout from the RAILWAY_HEALTHCHECK_TIMEOUT_SEC service variable, which a
    template can carry.
    """
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "image", "image": "img:1"},
                    "deploy": {"healthcheckPath": "/healthz", "healthcheckTimeout": 450},
                }
            ]
        )
    )
    service = only_service(config)
    assert "healthcheckTimeout" not in service["deploy"]
    assert service["variables"]["RAILWAY_HEALTHCHECK_TIMEOUT_SEC"]["defaultValue"] == "450"


def test_an_explicit_timeout_variable_is_not_overwritten():
    config = rt_payload.build_serialized_config(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "image", "image": "img:1"},
                    "variables": {"RAILWAY_HEALTHCHECK_TIMEOUT_SEC": {"value": "900"}},
                    "deploy": {"healthcheckTimeout": 450},
                }
            ]
        )
    )
    assert only_service(config)["variables"]["RAILWAY_HEALTHCHECK_TIMEOUT_SEC"]["defaultValue"] == "900"


def test_build_deploy_input_carries_the_config_and_project():
    template = template_with([{"name": "app", "source": {"type": "image", "image": "img:1"}}])
    payload = rt_payload.build_deploy_input(template, project_id="prj_1", environment_id="env_1")
    assert payload["projectId"] == "prj_1"
    assert payload["environmentId"] == "env_1"
    assert payload["serializedConfig"] == rt_payload.build_serialized_config(template)


def test_build_deploy_input_omits_unset_targets():
    template = template_with([{"name": "app", "source": {"type": "image", "image": "img:1"}}])
    payload = rt_payload.build_deploy_input(template, workspace_id="ws_1")
    assert payload["workspaceId"] == "ws_1"
    assert "projectId" not in payload
    assert "environmentId" not in payload


def test_build_publish_input_carries_the_marketplace_metadata(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Aptabase\n")
    template = template_with([{"name": "app", "source": {"type": "image", "image": "img:1"}}])
    template["readme"] = str(readme)
    payload = rt_payload.build_publish_input(template)
    assert payload["category"] == "Analytics"
    assert payload["description"] == "An example template."
    assert payload["readme"] == "# Aptabase\n"


def test_build_publish_input_without_a_readme_sends_none():
    template = template_with([{"name": "app", "source": {"type": "image", "image": "img:1"}}])
    assert rt_payload.build_publish_input(template)["readme"] is None


# --- the real template -------------------------------------------------------


@pytest.fixture(scope="module")
def aptabase_config():
    return rt_payload.build_serialized_config(rt_schema.load_template(TEMPLATE_PATH))


def test_the_aptabase_config_serialises_to_json(aptabase_config):
    assert json.dumps(aptabase_config)


def test_the_aptabase_config_has_all_three_services(aptabase_config):
    names = sorted(service["name"] for service in aptabase_config["services"].values())
    assert names == ["aptabase", "clickhouse", "postgres"]


def test_the_aptabase_app_is_the_only_public_service(aptabase_config):
    public = [s["name"] for s in aptabase_config["services"].values() if s["networking"]]
    assert public == ["aptabase"]


def test_the_aptabase_databases_keep_their_volumes(aptabase_config):
    mounts = {
        service["name"]: service["deploy"].get("requiredMountPath")
        for service in aptabase_config["services"].values()
    }
    assert mounts["postgres"] == "/var/lib/postgresql/data"
    assert mounts["clickhouse"] == "/var/lib/clickhouse"
    assert mounts["aptabase"] is None


def test_the_aptabase_clickhouse_root_directory_is_absolute(aptabase_config):
    clickhouse = next(
        s for s in aptabase_config["services"].values() if s["name"] == "clickhouse"
    )
    assert clickhouse["source"]["rootDirectory"] == "/templates/aptabase/clickhouse"


def test_the_aptabase_cross_service_references_name_real_services(aptabase_config):
    names = {service["name"] for service in aptabase_config["services"].values()}
    app = next(s for s in aptabase_config["services"].values() if s["name"] == "aptabase")
    database_url = app["variables"]["DATABASE_URL"]["defaultValue"]
    assert "${{postgres." in database_url
    assert "postgres" in names
