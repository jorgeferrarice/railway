import rt_lint


def template_with(services):
    return {
        "name": "Example",
        "description": "An example template.",
        "category": "Analytics",
        "services": services,
    }


def test_a_clean_template_reports_nothing():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": "hunter2"}},
            },
            {
                "name": "app",
                "source": {
                    "type": "image",
                    "image": "ghcr.io/example/app@sha256:" + "a" * 64,
                },
                "variables": {
                    "DB": {"value": "Password=${{db.PASSWORD}};Host=${{db.RAILWAY_PRIVATE_DOMAIN}}"}
                },
            },
        ]
    )
    assert rt_lint.lint_template(template) == []


def test_reference_to_an_unknown_service_is_reported():
    template = template_with(
        [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"DB": {"value": "${{cache.PASSWORD}}"}},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("cache" in problem for problem in problems)


def test_reference_to_an_unknown_variable_is_reported():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": "hunter2"}},
            },
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"DB": {"value": "${{db.USERNAME}}"}},
            },
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("USERNAME" in problem for problem in problems)


def test_railway_provided_variables_are_not_treated_as_unknown():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {},
            },
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"HOST": {"value": "${{db.RAILWAY_PRIVATE_DOMAIN}}"}},
            },
        ]
    )
    assert rt_lint.lint_template(template) == []


def test_unqualified_reference_to_an_own_variable_is_allowed():
    template = template_with(
        [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {
                    "PORT": {"value": "8080"},
                    "URL": {"value": "http://localhost:${{PORT}}"},
                },
            }
        ]
    )
    assert rt_lint.lint_template(template) == []


def test_secret_alphabet_with_delimiters_is_reported():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": '${{secret(32, "abc;=")}}'}},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("alphabet" in problem for problem in problems)


def test_secret_without_an_explicit_alphabet_is_reported():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {"PASSWORD": {"value": "${{secret(32)}}"}},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("alphabet" in problem for problem in problems)


def test_floating_tag_on_a_digest_pinned_registry_is_reported():
    template = template_with(
        [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/aptabase/aptabase:main"},
                "variables": {},
            }
        ]
    )
    problems = rt_lint.lint_template(template)
    assert any("digest" in problem for problem in problems)


def test_a_service_with_a_volume_and_no_mount_path_conflict_is_clean():
    template = template_with(
        [
            {
                "name": "db",
                "source": {"type": "image", "image": "ghcr.io/example/db:1.0.0"},
                "variables": {},
                "volumes": [{"mountPath": "/var/lib/db"}],
            }
        ]
    )
    assert rt_lint.lint_template(template) == []
