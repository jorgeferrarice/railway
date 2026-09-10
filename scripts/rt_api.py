"""Minimal Railway GraphQL client.

The token comes from the RAILWAY_API_TOKEN environment variable and nowhere
else. The Railway CLI's stored credentials are deliberately never read.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import rt_http

API_URL = "https://backboard.railway.com/graphql/v2"

# Cloudflare fronts the Railway API and refuses urllib's default User-Agent
# with a 403 carrying "error code: 1010". Name the client instead.
USER_AGENT = "railway-templates/1.0 (+https://github.com/jorgeferrarice/railway)"

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


def _error_body(error: urllib.error.HTTPError) -> str:
    """Read an HTTPError's body, which is where Railway explains the refusal."""
    try:
        return error.read().decode(errors="replace").strip() or "<empty body>"
    except Exception:
        return "<unreadable body>"


def _default_opener(request):
    return urllib.request.urlopen(request, timeout=60, context=rt_http.ssl_context())


def graphql(
    query: str,
    variables: dict | None = None,
    *,
    token: str | None = None,
    project_token: bool = False,
    opener=None,
) -> dict:
    """Execute a GraphQL document and return its data object.

    Railway authenticates account and team tokens with a Bearer header, and
    project tokens with a Project-Access-Token header. Sending the wrong one
    yields a bare 403, so which token is in hand has to be stated.
    """
    opener = opener or _default_opener
    token = token or get_token()
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    auth = {"Project-Access-Token": token} if project_token else {"Authorization": f"Bearer {token}"}
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT, **auth},
        method="POST",
    )
    try:
        with opener(request) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise RailwayAPIError(f"HTTP {error.code} {error.reason}: {_error_body(error)}") from error

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
