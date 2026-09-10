"""Shared HTTPS trust configuration.

Python's default SSL context trusts whatever CA bundle the interpreter was
built against. That is not dependable: PlatformIO's portable Python, which ships
on some developer machines and can win the PATH race, reports a CA file path
from the machine that built it. The file does not exist locally, so the default
context verifies nothing and every HTTPS request dies with
CERTIFICATE_VERIFY_FAILED.

Certificates are therefore taken from certifi, which is pinned in
requirements-dev.txt and present wherever this repository is checked out.
"""

from __future__ import annotations

import functools
import ssl

import certifi


@functools.lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    """Return a verifying SSL context backed by certifi's CA bundle."""
    return ssl.create_default_context(cafile=certifi.where())
