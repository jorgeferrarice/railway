#!/usr/bin/env python3
"""Manage Railway templates from version-controlled definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bump_digest
import rt_api
import rt_lint
import rt_schema


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
