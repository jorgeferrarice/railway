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
        raise DigestResolutionError(f"service {service!r} is not digest-pinned: {old_image!r}")

    reference, old_digest = old_image.split("@", 1)
    repository = reference.split("/", 1)[1]
    new_digest = resolve_digest(repository, tag, opener=opener)
    new_image = f"{reference}@{new_digest}"

    if new_digest != old_digest:
        # Replace the digest textually so the diff stays one line and the rest
        # of the file's formatting survives untouched.
        template_path.write_text(template_path.read_text().replace(old_digest, new_digest))

    return old_image, new_image
