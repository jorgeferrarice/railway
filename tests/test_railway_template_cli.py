import json

import pytest

import railway_template
import rt_api

TEMPLATE = "templates/aptabase/template.json"


@pytest.fixture
def recorded(monkeypatch):
    """Record GraphQL calls and answer them, so no test reaches the network."""
    calls = []

    def fake_graphql(query, variables=None, **kwargs):
        calls.append((query, variables))
        if "templateDeployV2" in query:
            return {"templateDeployV2": {"projectId": "prj_123", "workflowId": "wf_1"}}
        if "templateGenerate" in query:
            return {"templateGenerate": {"id": "tpl_123", "code": "aptabase"}}
        if "templatePublish" in query:
            return {"templatePublish": {"id": "tpl_123", "code": "aptabase"}}
        return {}

    monkeypatch.setattr(railway_template.rt_api, "graphql", fake_graphql)
    monkeypatch.setenv("RAILWAY_API_TOKEN", "tok")
    return calls


def test_render_prints_the_serialized_config(capsys):
    assert railway_template.main(["render", TEMPLATE]) == 0
    config = json.loads(capsys.readouterr().out)
    names = sorted(service["name"] for service in config["services"].values())
    assert names == ["aptabase", "clickhouse", "postgres"]


def test_render_needs_no_token(monkeypatch, capsys):
    monkeypatch.delenv("RAILWAY_API_TOKEN", raising=False)
    assert railway_template.main(["render", TEMPLATE]) == 0


def test_render_refuses_a_template_that_fails_lint(tmp_path, capsys):
    broken = tmp_path / "template.json"
    broken.write_text(
        json.dumps(
            {
                "name": "Broken",
                "description": "d",
                "category": "Analytics",
                "services": [
                    {
                        "name": "app",
                        "source": {"type": "image", "image": "ghcr.io/aptabase/aptabase:main"},
                        "variables": {},
                    }
                ],
            }
        )
    )
    assert railway_template.main(["render", str(broken)]) == 1
    assert "digest" in capsys.readouterr().err


def test_deploy_sends_the_serialized_config(recorded, capsys):
    assert railway_template.main(["deploy", TEMPLATE, "--project-id", "prj_123"]) == 0
    query, variables = recorded[0]
    assert "templateDeployV2" in query
    assert variables["input"]["projectId"] == "prj_123"
    assert "services" in variables["input"]["serializedConfig"]
    assert "prj_123" in capsys.readouterr().out


def test_deploy_accepts_a_workspace_instead_of_a_project(recorded):
    assert railway_template.main(["deploy", TEMPLATE, "--workspace-id", "ws_1"]) == 0
    _, variables = recorded[0]
    assert variables["input"]["workspaceId"] == "ws_1"
    assert "projectId" not in variables["input"]


def test_deploy_requires_a_target(recorded, capsys):
    assert railway_template.main(["deploy", TEMPLATE]) == 1
    assert "--project-id" in capsys.readouterr().err


def test_deploy_can_stage_without_applying(recorded):
    assert railway_template.main(["deploy", TEMPLATE, "--project-id", "prj_1", "--stage-only"]) == 0
    _, variables = recorded[0]
    assert variables["input"]["stageOnly"] is True


def test_deploy_refuses_a_template_that_fails_lint(tmp_path, recorded, capsys):
    broken = tmp_path / "template.json"
    broken.write_text(
        json.dumps(
            {
                "name": "Broken",
                "description": "d",
                "category": "Analytics",
                "services": [
                    {
                        "name": "app",
                        "source": {"type": "image", "image": "ghcr.io/aptabase/aptabase:main"},
                        "variables": {},
                    }
                ],
            }
        )
    )
    assert railway_template.main(["deploy", str(broken), "--project-id", "prj_1"]) == 1
    assert recorded == []


def test_generate_turns_a_project_into_a_template(recorded, capsys):
    assert railway_template.main(["generate", "--project-id", "prj_1", "--environment-id", "env_1"]) == 0
    query, variables = recorded[0]
    assert "templateGenerate" in query
    assert variables["input"] == {"projectId": "prj_1", "environmentId": "env_1"}
    assert "tpl_123" in capsys.readouterr().out


def test_generate_requires_a_project(recorded):
    with pytest.raises(SystemExit):
        railway_template.main(["generate"])


def test_publish_sends_the_marketplace_metadata(recorded, capsys):
    assert railway_template.main(["publish", TEMPLATE, "--template-id", "tpl_123"]) == 0
    query, variables = recorded[0]
    assert "templatePublish" in query
    assert variables["id"] == "tpl_123"
    assert variables["input"]["category"] == "Analytics"
    assert variables["input"]["readme"].startswith(
        "# Deploy and Host Aptabase with Railway"
    )


def test_publish_requires_a_template_id(recorded):
    with pytest.raises(SystemExit):
        railway_template.main(["publish", TEMPLATE])


def test_api_errors_become_exit_code_one(monkeypatch, capsys):
    def failing(*args, **kwargs):
        raise rt_api.RailwayAPIError("Not authorized")

    monkeypatch.setattr(railway_template.rt_api, "graphql", failing)
    monkeypatch.setenv("RAILWAY_API_TOKEN", "tok")
    assert railway_template.main(["deploy", TEMPLATE, "--project-id", "prj_1"]) == 1
    assert "Not authorized" in capsys.readouterr().err


def test_a_missing_token_is_reported_clearly(monkeypatch, capsys):
    monkeypatch.delenv("RAILWAY_API_TOKEN", raising=False)
    assert railway_template.main(["deploy", TEMPLATE, "--project-id", "prj_1"]) == 1
    assert "RAILWAY_API_TOKEN" in capsys.readouterr().err
