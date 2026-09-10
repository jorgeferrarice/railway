import ssl

import rt_http


def test_ssl_context_verifies_certificates():
    context = rt_http.ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_ssl_context_has_a_usable_trust_store():
    """The interpreter's own store is not trusted to exist.

    PlatformIO's portable Python, which is first on PATH on this machine,
    reports a CA file path from the machine that built it, so the default
    context verifies nothing and every HTTPS call fails.
    """
    assert rt_http.ssl_context().get_ca_certs()


def test_ssl_context_is_cached():
    assert rt_http.ssl_context() is rt_http.ssl_context()
