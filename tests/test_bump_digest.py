import io
import json

import pytest

import bump_digest

NEW_DIGEST = "sha256:" + "b" * 64
OLD_DIGEST = "sha256:" + "a" * 64


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def fake_registry(digest=NEW_DIGEST, calls=None):
    def opener(request):
        if calls is not None:
            calls.append(request)
        if "/token" in request.full_url:
            return FakeResponse(json.dumps({"token": "fake-token"}).encode())
        return FakeResponse(headers={"Docker-Content-Digest": digest})

    return opener


def template_file(tmp_path, image):
    path = tmp_path / "template.json"
    path.write_text(
        json.dumps(
            {
                "name": "Example",
                "description": "An example template.",
                "category": "Analytics",
                "services": [
                    {
                        "name": "app",
                        "source": {"type": "image", "image": image},
                        "variables": {},
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )
    return path


def test_resolve_digest_returns_the_registry_digest():
    assert bump_digest.resolve_digest("aptabase/aptabase", "main", opener=fake_registry()) == NEW_DIGEST


def test_resolve_digest_requests_a_manifest_list():
    calls = []
    bump_digest.resolve_digest("aptabase/aptabase", "main", opener=fake_registry(calls=calls))
    manifest_request = calls[-1]
    assert manifest_request.get_method() == "HEAD"
    assert "manifest.list" in manifest_request.headers["Accept"]
    assert manifest_request.full_url.endswith("/manifests/main")


def test_resolve_digest_authenticates_with_the_pull_token():
    calls = []
    bump_digest.resolve_digest("aptabase/aptabase", "main", opener=fake_registry(calls=calls))
    assert calls[-1].headers["Authorization"] == "Bearer fake-token"


def test_resolve_digest_raises_when_the_registry_returns_no_digest():
    def opener(request):
        if "/token" in request.full_url:
            return FakeResponse(json.dumps({"token": "fake-token"}).encode())
        return FakeResponse(headers={})

    with pytest.raises(bump_digest.DigestResolutionError):
        bump_digest.resolve_digest("aptabase/aptabase", "main", opener=opener)


def test_current_image_reads_the_named_service(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    template = json.loads(path.read_text())
    assert bump_digest.current_image(template, "app") == f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}"


def test_current_image_raises_for_an_unknown_service(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    template = json.loads(path.read_text())
    with pytest.raises(KeyError):
        bump_digest.current_image(template, "nope")


def test_bump_rewrites_the_digest_in_place(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    old, new = bump_digest.bump(path, "app", "main", opener=fake_registry())
    assert old == f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}"
    assert new == f"ghcr.io/aptabase/aptabase@{NEW_DIGEST}"
    assert new in path.read_text()
    assert OLD_DIGEST not in path.read_text()


def test_bump_is_a_no_op_when_the_digest_is_unchanged(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{NEW_DIGEST}")
    before = path.read_text()
    old, new = bump_digest.bump(path, "app", "main", opener=fake_registry())
    assert old == new
    assert path.read_text() == before


def test_bump_preserves_the_rest_of_the_file_byte_for_byte(tmp_path):
    path = template_file(tmp_path, f"ghcr.io/aptabase/aptabase@{OLD_DIGEST}")
    before = path.read_text()
    bump_digest.bump(path, "app", "main", opener=fake_registry())
    after = path.read_text()
    assert after == before.replace(OLD_DIGEST, NEW_DIGEST)


def test_bump_rejects_a_service_that_is_not_digest_pinned(tmp_path):
    path = template_file(tmp_path, "ghcr.io/aptabase/aptabase:main")
    with pytest.raises(bump_digest.DigestResolutionError):
        bump_digest.bump(path, "app", "main", opener=fake_registry())
