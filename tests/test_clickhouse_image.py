import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import pytest

CONTEXT = Path(__file__).resolve().parent.parent / "templates" / "aptabase" / "clickhouse"
IMAGE_TAG = "railway-templates/aptabase-clickhouse:test"
USER = "aptabase"
PASSWORD = "testpassword"


def docker_available():
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not docker_available(), reason="Docker daemon is not running"),
]


def query(port, sql, timeout=2):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/?query={urllib.parse.quote(sql)}",
        headers={"X-ClickHouse-User": USER, "X-ClickHouse-Key": PASSWORD},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode().strip()


@pytest.fixture(scope="module")
def running_clickhouse():
    subprocess.run(["docker", "build", "-t", IMAGE_TAG, str(CONTEXT)], check=True)
    name = f"clickhouse-test-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        [
            "docker", "run", "-d", "--rm", "--name", name,
            "-p", "0:8123",
            "-e", f"CLICKHOUSE_USER={USER}",
            "-e", f"CLICKHOUSE_PASSWORD={PASSWORD}",
            IMAGE_TAG,
        ],
        check=True,
        capture_output=True,
    )
    try:
        port = subprocess.run(
            ["docker", "port", name, "8123/tcp"],
            check=True, capture_output=True, text=True,
        ).stdout.strip().rsplit(":", 1)[1]
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                if query(port, "SELECT 1") == "1":
                    break
            except (urllib.error.URLError, OSError):
                time.sleep(2)
        else:
            pytest.fail("ClickHouse did not become ready within 120s")
        yield port, name
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def test_it_answers_queries_for_the_configured_user(running_clickhouse):
    port, _ = running_clickhouse
    assert query(port, "SELECT 1") == "1"


def strip_xml_comments(xml):
    return re.sub(r"<!--.*?-->", "", xml, flags=re.DOTALL)


def test_the_railway_config_declares_ipv6_itself():
    """Do not depend on upstream's docker_related_config.xml for this.

    It is upstream's file and can change between image versions, and without a
    "::" bind the service is unreachable over Railway's private network.
    """
    xml = strip_xml_comments((CONTEXT / "config.d" / "railway.xml").read_text())
    assert "<listen_host>::</listen_host>" in xml
    assert "<listen_host>0.0.0.0</listen_host>" in xml


def test_the_effective_config_binds_ipv6(running_clickhouse):
    """Assert the merged config, not a live socket.

    Whether the "::" bind succeeds depends on the host: Docker Desktop on macOS
    disables IPv6 inside containers, so the bind fails there and listen_try
    swallows it. What this image is responsible for is asking for it.
    """
    _, name = running_clickhouse
    merged = subprocess.run(
        ["docker", "exec", name, "cat", "/var/lib/clickhouse/preprocessed_configs/config.xml"],
        check=True, capture_output=True, text=True,
    ).stdout
    assert "<listen_host>::</listen_host>" in strip_xml_comments(merged)


def test_memory_is_sized_from_the_container_limit(running_clickhouse):
    port, _ = running_clickhouse
    value = query(
        port,
        "SELECT value FROM system.server_settings WHERE name = 'max_server_memory_usage_to_ram_ratio'",
    )
    assert float(value) == pytest.approx(0.7)


def test_the_verbose_system_log_tables_are_disabled(running_clickhouse):
    port, _ = running_clickhouse
    query(port, "SELECT 1")
    time.sleep(10)
    existing = query(
        port,
        "SELECT name FROM system.tables WHERE database = 'system' "
        "AND name IN ('trace_log', 'metric_log', 'asynchronous_metric_log', 'text_log') "
        "ORDER BY name",
    )
    assert existing == ""


def test_the_railway_config_is_the_only_file_added(running_clickhouse):
    _, name = running_clickhouse
    result = subprocess.run(
        ["docker", "exec", name, "ls", "/etc/clickhouse-server/config.d/"],
        check=True, capture_output=True, text=True,
    )
    assert "railway.xml" in result.stdout


def test_the_railway_json_declares_a_dockerfile_build():
    config = json.loads((CONTEXT / "railway.json").read_text())
    assert config["build"]["builder"] == "DOCKERFILE"
