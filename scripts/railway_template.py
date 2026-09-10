#!/usr/bin/env python3
"""Manage Railway templates from version-controlled definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bump_digest
import rt_api
import rt_apply
import rt_lint
import rt_payload
import rt_schema

DEPLOY_MUTATION = """
mutation Deploy($input: TemplateDeployV2Input!) {
  templateDeployV2(input: $input) { projectId workflowId }
}
"""

GENERATE_MUTATION = """
mutation Generate($input: TemplateGenerateInput!) {
  templateGenerate(input: $input) { id code name }
}
"""

PUBLISH_MUTATION = """
mutation Publish($id: String!, $input: TemplatePublishInput!) {
  templatePublish(id: $id, input: $input) { id code name }
}
"""


def _load_checked(path: str) -> dict | None:
    """Load a template and refuse it if the linter objects.

    A definition that fails lint must never reach Railway: the checks catch
    dangling cross-service references and unpinned images, which produce a
    broken deploy rather than a clean error.
    """
    template = rt_schema.load_template(Path(path))
    problems = rt_lint.lint_template(template)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    return None if problems else template


def cmd_validate(args) -> int:
    """Schema-validate a template definition."""
    try:
        rt_schema.load_template(Path(args.template))
    except rt_schema.TemplateValidationError as error:
        for problem in error.errors:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    print(f"{args.template}: valid")
    return 0


def cmd_lint(args) -> int:
    """Check cross-service references and repository invariants."""
    template = rt_schema.load_template(Path(args.template))
    problems = rt_lint.lint_template(template)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"{args.template}: clean")
    return 0


def cmd_introspect(args) -> int:
    """Print the GraphQL types needed to build template payloads."""
    if args.mutations:
        for name in rt_api.find_mutations(args.mutations):
            print(name)
        return 0
    for name in args.types:
        print(json.dumps(rt_api.describe_type(name), indent=2))
    return 0


def cmd_bump(args) -> int:
    """Re-resolve a digest-pinned image and rewrite the template."""
    old, new = bump_digest.bump(Path(args.template), args.service, args.tag)
    if old == new:
        print(f"{args.service}: already current ({new})")
    else:
        print(f"{args.service}: {old}\n{' ' * (len(args.service) + 2)}-> {new}")
    return 0


def cmd_render(args) -> int:
    """Print the serializedConfig this template would send to Railway."""
    template = _load_checked(args.template)
    if template is None:
        return 1
    print(json.dumps(rt_payload.build_serialized_config(template), indent=2))
    return 0


def cmd_deploy(args) -> int:
    """Deploy the template definition into a project."""
    template = _load_checked(args.template)
    if template is None:
        return 1
    if not (args.project_id or args.workspace_id):
        print("error: one of --project-id or --workspace-id is required", file=sys.stderr)
        return 1

    payload = rt_payload.build_deploy_input(
        template,
        project_id=args.project_id,
        environment_id=args.environment_id,
        workspace_id=args.workspace_id,
    )
    if args.stage_only:
        payload["stageOnly"] = True

    result = rt_api.graphql(DEPLOY_MUTATION, {"input": payload})["templateDeployV2"]
    print(f"project:  {result['projectId']}")
    print(f"workflow: {result['workflowId']}")
    return 0


def cmd_apply(args) -> int:
    """Build the template's services directly in a project.

    The route to use because templateDeployV2 is refused from the public API;
    see docs/railway-template-api.md.
    """
    template = _load_checked(args.template)
    if template is None:
        return 1
    ids = rt_apply.apply_template(template, args.project_id, args.environment_id)
    for name, service_id in ids.items():
        print(f"{name}: {service_id}")
    return 0


def cmd_generate(args) -> int:
    """Turn a deployed project into a stored template.

    Railway has no mutation that registers a template from a definition; a
    template is always generated from a project that already exists.
    """
    payload = {"projectId": args.project_id}
    if args.environment_id:
        payload["environmentId"] = args.environment_id
    result = rt_api.graphql(GENERATE_MUTATION, {"input": payload})["templateGenerate"]
    print(f"template id:   {result['id']}")
    print(f"template code: {result.get('code')}")
    return 0


def cmd_publish(args) -> int:
    """Publish a stored template to the marketplace."""
    template = _load_checked(args.template)
    if template is None:
        return 1
    payload = rt_payload.build_publish_input(template, workspace_id=args.workspace_id)
    result = rt_api.graphql(
        PUBLISH_MUTATION, {"id": args.template_id, "input": payload}
    )["templatePublish"]
    print(f"published: {result['id']} ({result.get('code')})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="railway_template", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="schema-validate a template definition")
    validate.add_argument("template")
    validate.set_defaults(func=cmd_validate)

    lint = subparsers.add_parser("lint", help="check references and invariants")
    lint.add_argument("template")
    lint.set_defaults(func=cmd_lint)

    introspect = subparsers.add_parser("introspect", help="read the Railway GraphQL schema")
    introspect.add_argument("types", nargs="*", help="type names to describe")
    introspect.add_argument("--mutations", help="list mutation names containing this substring")
    introspect.set_defaults(func=cmd_introspect)

    bump = subparsers.add_parser("bump", help="re-resolve a pinned image digest")
    bump.add_argument("template")
    bump.add_argument("--service", required=True)
    bump.add_argument("--tag", default="main")
    bump.set_defaults(func=cmd_bump)

    render = subparsers.add_parser("render", help="print the serializedConfig payload")
    render.add_argument("template")
    render.set_defaults(func=cmd_render)

    deploy = subparsers.add_parser("deploy", help="deploy the definition into a project")
    deploy.add_argument("template")
    deploy.add_argument("--project-id")
    deploy.add_argument("--environment-id")
    deploy.add_argument("--workspace-id")
    deploy.add_argument(
        "--stage-only",
        action="store_true",
        help="stage the changes without applying them",
    )
    deploy.set_defaults(func=cmd_deploy)

    apply_cmd = subparsers.add_parser(
        "apply", help="build the template's services directly in a project"
    )
    apply_cmd.add_argument("template")
    apply_cmd.add_argument("--project-id", required=True)
    apply_cmd.add_argument("--environment-id", required=True)
    apply_cmd.set_defaults(func=cmd_apply)

    generate = subparsers.add_parser(
        "generate", help="turn a deployed project into a stored template"
    )
    generate.add_argument("--project-id", required=True)
    generate.add_argument("--environment-id")
    generate.set_defaults(func=cmd_generate)

    publish = subparsers.add_parser("publish", help="publish a stored template")
    publish.add_argument("template")
    publish.add_argument("--template-id", required=True)
    publish.add_argument("--workspace-id")
    publish.set_defaults(func=cmd_publish)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (rt_api.RailwayAPIError, bump_digest.DigestResolutionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
