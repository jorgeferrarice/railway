import json

import pytest

import rt_schema


def minimal_template():
    return {
        "name": "Example",
        "description": "An example template.",
        "category": "Analytics",
        "services": [
            {
                "name": "app",
                "source": {"type": "image", "image": "ghcr.io/example/app:1.0.0"},
                "variables": {"PORT": {"value": "8080"}},
            }
        ],
    }


def test_load_schema_returns_a_draft_2020_12_schema():
    schema = rt_schema.load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_minimal_template_validates():
    rt_schema.validate_template(minimal_template())


def test_missing_name_is_rejected():
    template = minimal_template()
    del template["name"]
    with pytest.raises(rt_schema.TemplateValidationError) as excinfo:
        rt_schema.validate_template(template)
    assert any("name" in error for error in excinfo.value.errors)


def test_unknown_source_type_is_rejected():
    template = minimal_template()
    template["services"][0]["source"] = {"type": "helm", "chart": "nope"}
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.validate_template(template)


def test_repo_source_requires_a_root_directory():
    template = minimal_template()
    template["services"][0]["source"] = {"type": "repo", "repo": "owner/name"}
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.validate_template(template)


def test_variable_value_must_be_a_string():
    template = minimal_template()
    template["services"][0]["variables"]["PORT"] = {"value": 8080}
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.validate_template(template)


def test_duplicate_service_names_are_rejected():
    template = minimal_template()
    template["services"].append(dict(template["services"][0]))
    with pytest.raises(rt_schema.TemplateValidationError) as excinfo:
        rt_schema.validate_template(template)
    assert any("duplicate" in error.lower() for error in excinfo.value.errors)


def test_all_errors_are_reported_not_just_the_first():
    template = minimal_template()
    del template["name"]
    del template["description"]
    with pytest.raises(rt_schema.TemplateValidationError) as excinfo:
        rt_schema.validate_template(template)
    assert len(excinfo.value.errors) >= 2


def test_load_template_reads_and_validates(tmp_path):
    path = tmp_path / "template.json"
    path.write_text(json.dumps(minimal_template()))
    assert rt_schema.load_template(path)["name"] == "Example"


def test_load_template_raises_on_an_invalid_file(tmp_path):
    path = tmp_path / "template.json"
    path.write_text(json.dumps({"name": "Broken"}))
    with pytest.raises(rt_schema.TemplateValidationError):
        rt_schema.load_template(path)
