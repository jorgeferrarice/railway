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


def graphql(
    query: str,
    variables: dict | None = None,
    *,
    token: str | None = None,
    opener=None,
) -> dict:
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
