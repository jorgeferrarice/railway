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
