import pytest

import rt_apply

PROJECT = "prj_1"
ENVIRONMENT = "env_1"


def template_with(services):
    return {
        "name": "Example",
        "description": "An example template.",
        "category": "Analytics",
        "services": services,
    }


class FakeAPI:
    """Records every mutation and answers with plausible ids."""

    def __init__(self):
        self.calls = []
        self._next = 0

    def __call__(self, query, variables=None, **kwargs):
        name = next(
            word
            for word in ("serviceCreate", "serviceInstanceUpdate", "variableCollectionUpsert",
                         "volumeCreate", "serviceDomainCreate")
            if word in query
        )
        self.calls.append((name, variables))
        self._next += 1
        if name == "serviceCreate":
            return {"serviceCreate": {"id": f"svc_{self._next}", "name": variables["input"]["name"]}}
        if name == "volumeCreate":
            return {"volumeCreate": {"id": f"vol_{self._next}"}}
        if name == "serviceDomainCreate":
            return {"serviceDomainCreate": {"domain": "example.up.railway.app"}}
        return {name: True}

    def named(self, name):
        return [variables for called, variables in self.calls if called == name]

    @property
    def order(self):
        return [called for called, _ in self.calls]


@pytest.fixture
def api():
    return FakeAPI()


def apply(template, api):
    return rt_apply.apply_template(template, PROJECT, ENVIRONMENT, graphql=api)


def test_every_service_is_created(api):
    apply(
        template_with(
            [
                {"name": "db", "source": {"type": "image", "image": "img:1"}},
                {"name": "app", "source": {"type": "image", "image": "img:2"}},
            ]
        ),
        api,
    )
    assert [v["input"]["name"] for v in api.named("serviceCreate")] == ["db", "app"]


def test_all_services_exist_before_any_variables_are_set(api):
    """A variable like ${{db.PASSWORD}} cannot resolve until db exists, so
    every service is created before any variable collection is upserted.
    """
    apply(
        template_with(
            [
                {"name": "db", "source": {"type": "image", "image": "img:1"},
                 "variables": {"PASSWORD": {"value": "x"}}},
                {"name": "app", "source": {"type": "image", "image": "img:2"},
                 "variables": {"DB": {"value": "${{db.PASSWORD}}"}}},
            ]
        ),
        api,
    )
    last_create = max(i for i, name in enumerate(api.order) if name == "serviceCreate")
    first_variables = min(i for i, name in enumerate(api.order) if name == "variableCollectionUpsert")
    assert last_create < first_variables


def test_services_are_created_without_variables(api):
    apply(
        template_with(
            [{"name": "db", "source": {"type": "image", "image": "img:1"},
              "variables": {"A": {"value": "1"}}}]
        ),
        api,
    )
    assert "variables" not in api.named("serviceCreate")[0]["input"]


def test_variables_are_sent_as_plain_name_to_value(api):
    apply(
        template_with(
            [{"name": "db", "source": {"type": "image", "image": "img:1"},
              "variables": {"A": {"value": "1", "description": "d", "isOptional": True}}}]
        ),
        api,
    )
    payload = api.named("variableCollectionUpsert")[0]["input"]
    assert payload["variables"] == {"A": "1"}
    assert payload["serviceId"] == "svc_1"
    assert payload["projectId"] == PROJECT
    assert payload["environmentId"] == ENVIRONMENT


def test_an_image_source_is_passed_to_service_create(api):
    apply(template_with([{"name": "db", "source": {"type": "image", "image": "img:1"}}]), api)
    assert api.named("serviceCreate")[0]["input"]["source"] == {"image": "img:1"}


def test_a_repo_source_carries_the_branch_and_root_directory(api):
    apply(
        template_with(
            [
                {
                    "name": "ch",
                    "source": {
                        "type": "repo",
                        "repo": "owner/name",
                        "rootDirectory": "templates/x",
                        "branch": "main",
                    },
                }
            ]
        ),
        api,
    )
    created = api.named("serviceCreate")[0]["input"]
    assert created["source"] == {"repo": "owner/name"}
    assert created["branch"] == "main"
    update = api.named("serviceInstanceUpdate")[0]["input"]
    assert update["rootDirectory"] == "/templates/x"


def test_deploy_settings_are_applied(api):
    apply(
        template_with(
            [
                {
                    "name": "app",
                    "source": {"type": "image", "image": "img:1"},
                    "deploy": {
                        "healthcheckPath": "/healthz",
                        "healthcheckTimeout": 300,
                        "restartPolicyType": "ON_FAILURE",
                        "restartPolicyMaxRetries": 10,
                    },
                }
            ]
        ),
        api,
    )
    update = api.named("serviceInstanceUpdate")[0]["input"]
    assert update["healthcheckPath"] == "/healthz"
    assert update["healthcheckTimeout"] == 300
    assert update["restartPolicyType"] == "ON_FAILURE"
    assert update["restartPolicyMaxRetries"] == 10


def test_a_service_with_nothing_to_update_skips_the_update_call(api):
    apply(template_with([{"name": "db", "source": {"type": "image", "image": "img:1"}}]), api)
    assert api.named("serviceInstanceUpdate") == []


def test_volumes_are_created_on_the_right_service(api):
    apply(
        template_with(
            [
                {"name": "db", "source": {"type": "image", "image": "img:1"},
                 "volumes": [{"mountPath": "/var/lib/db"}]}
            ]
        ),
        api,
    )
    volume = api.named("volumeCreate")[0]["input"]
    assert volume["mountPath"] == "/var/lib/db"
    assert volume["serviceId"] == "svc_1"


def test_a_public_service_gets_a_domain_on_its_target_port(api):
    apply(
        template_with(
            [
                {"name": "app", "source": {"type": "image", "image": "img:1"},
                 "networking": {"http": {"targetPort": 8080}}}
            ]
        ),
        api,
    )
    domain = api.named("serviceDomainCreate")[0]["input"]
    assert domain["targetPort"] == 8080
    assert domain["serviceId"] == "svc_1"


def test_a_private_service_gets_no_domain(api):
    apply(template_with([{"name": "db", "source": {"type": "image", "image": "img:1"}}]), api)
    assert api.named("serviceDomainCreate") == []


def test_it_returns_the_created_service_ids_by_name(api):
    result = apply(
        template_with(
            [
                {"name": "db", "source": {"type": "image", "image": "img:1"}},
                {"name": "app", "source": {"type": "image", "image": "img:2"}},
            ]
        ),
        api,
    )
    assert result == {"db": "svc_1", "app": "svc_2"}
