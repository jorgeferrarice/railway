import io
import json
import urllib.error

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


def test_graphql_identifies_this_client_by_user_agent():
    """Cloudflare fronts the Railway API and answers urllib's default
    User-Agent with a 403 (error code 1010), so the client names itself.
    """
    calls = []
    opener = fake_transport({"data": {}}, calls=calls)
    rt_api.graphql("query { me { id } }", token="tok", opener=opener)
    assert calls[0].headers["User-agent"] == rt_api.USER_AGENT
    assert "urllib" not in rt_api.USER_AGENT


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


def test_an_http_error_becomes_a_railway_api_error_carrying_the_body():
    def opener(request):
        raise urllib.error.HTTPError(
            rt_api.API_URL, 403, "Forbidden", {}, io.BytesIO(b'{"message":"Not Authorized"}')
        )

    with pytest.raises(rt_api.RailwayAPIError) as excinfo:
        rt_api.graphql("query { me { id } }", token="tok", opener=opener)
    message = str(excinfo.value)
    assert "403" in message
    assert "Not Authorized" in message


def test_an_http_error_with_an_unreadable_body_still_reports_the_status():
    def opener(request):
        raise urllib.error.HTTPError(rt_api.API_URL, 500, "Server Error", {}, None)

    with pytest.raises(rt_api.RailwayAPIError) as excinfo:
        rt_api.graphql("query { me { id } }", token="tok", opener=opener)
    assert "500" in str(excinfo.value)


def test_a_project_token_uses_the_project_access_token_header():
    calls = []
    opener = fake_transport({"data": {}}, calls=calls)
    rt_api.graphql("query { me { id } }", token="tok", project_token=True, opener=opener)
    headers = calls[0].headers
    assert headers.get("Project-access-token") == "tok"
    assert "Authorization" not in headers


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
