# Graph Report - railway  (2026-09-10)

## Corpus Check
- 28 files · ~17,806 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 380 nodes · 447 edges · 27 communities
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ae62f744`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- template.schema.json
- $defs
- properties
- bump_digest.py
- Aptabase Railway Template — Design
- test_aptabase_template.py
- railway_template.py
- Aptabase Railway Template Implementation Plan
- test_rt_api.py
- rt_api.py
- test_bump_digest.py
- rt_schema.py
- test_clickhouse_image.py
- properties
- properties
- Aptabase
- test_rt_schema.py
- `serializedConfig`
- test_rt_lint.py
- Railway templates
- railway.json
- variable

## God Nodes (most connected - your core abstractions)
1. `Aptabase Railway Template Implementation Plan` - 18 edges
2. `Aptabase Railway Template — Design` - 14 edges
3. `Aptabase` - 11 edges
4. `fake_transport()` - 10 edges
5. `template_with()` - 10 edges
6. `minimal_template()` - 9 edges
7. `fake_registry()` - 8 edges
8. `build_parser()` - 7 edges
9. `graphql()` - 7 edges
10. `template_file()` - 7 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (27 total, 0 thin omitted)

### Community 0 - "template.schema.json"
Cohesion: 0.10
Nodes (20): additionalProperties, minLength, type, $id, $ref, type, properties, category (+12 more)

### Community 1 - "$defs"
Cohesion: 0.07
Nodes (29): minLength, type, $defs, imageSource, repoSource, service, minLength, type (+21 more)

### Community 2 - "properties"
Cohesion: 0.08
Nodes (24): $ref, additionalProperties, properties, required, type, minLength, pattern, type (+16 more)

### Community 3 - "bump_digest.py"
Cohesion: 0.10
Nodes (18): bump(), current_image(), DigestResolutionError, _HeadRequest, Path, RuntimeError, Re-resolve a digest-pinned image to the current digest behind its tag., Raised when a digest cannot be resolved or applied. (+10 more)

### Community 4 - "Aptabase Railway Template — Design"
Cohesion: 0.09
Nodes (21): `aptabase`, Aptabase Railway Template — Design, Background, `bump-digest.sh`, `clickhouse`, Data flow, Decisions recorded, Environment variables read by Aptabase (+13 more)

### Community 5 - "test_aptabase_template.py"
Cohesion: 0.09
Nodes (5): fixture, Railway health-checks the port named by PORT, not the target port. Kestrel is…, services(), template(), test_port_is_pinned_so_health_checks_probe_the_right_port()

### Community 6 - "railway_template.py"
Cohesion: 0.14
Nodes (18): ArgumentParser, build_parser(), cmd_bump(), cmd_introspect(), cmd_lint(), cmd_validate(), main(), Schema-validate a template definition. (+10 more)

### Community 7 - "Aptabase Railway Template Implementation Plan"
Cohesion: 0.10
Nodes (19): Aptabase Railway Template Implementation Plan, Deviation from the spec, File Structure, Global Constraints, Self-Review, Task 10: Create, update, publish and deploy subcommands, Task 11: Template README and marketplace listing, Task 12: Push the repository to GitHub (+11 more)

### Community 8 - "test_rt_api.py"
Cohesion: 0.15
Nodes (12): fake_transport(), FakeResponse, Cloudflare fronts the Railway API and answers urllib's default User-Agent with…, test_a_project_token_uses_the_project_access_token_header(), test_describe_type_raises_for_an_unknown_type(), test_describe_type_returns_the_input_fields(), test_find_mutations_filters_case_insensitively(), test_graphql_identifies_this_client_by_user_agent() (+4 more)

### Community 9 - "rt_api.py"
Cohesion: 0.15
Nodes (17): HTTPError, describe_type(), _error_body(), find_mutations(), get_token(), graphql(), MissingTokenError, RuntimeError (+9 more)

### Community 10 - "test_bump_digest.py"
Cohesion: 0.21
Nodes (12): fake_registry(), FakeResponse, template_file(), test_bump_is_a_no_op_when_the_digest_is_unchanged(), test_bump_preserves_the_rest_of_the_file_byte_for_byte(), test_bump_rejects_a_service_that_is_not_digest_pinned(), test_bump_rewrites_the_digest_in_place(), test_current_image_raises_for_an_unknown_service() (+4 more)

### Community 11 - "rt_schema.py"
Cohesion: 0.18
Nodes (13): _duplicate_service_errors(), load_schema(), load_template(), Path, Load and validate Railway template definitions., Raised when a template definition does not match the schema., Read the template JSON Schema from disk., Raise TemplateValidationError if the template does not match the schema.… (+5 more)

### Community 12 - "test_clickhouse_image.py"
Cohesion: 0.19
Nodes (11): fixture, query(), Do not depend on upstream's docker_related_config.xml for this. It is…, Assert the merged config, not a live socket. Whether the "::" bind succeeds…, running_clickhouse(), strip_xml_comments(), test_it_answers_queries_for_the_configured_user(), test_memory_is_sized_from_the_container_limit() (+3 more)

### Community 13 - "properties"
Cohesion: 0.19
Nodes (13): additionalProperties, properties, required, type, minLength, type, items, label (+5 more)

### Community 14 - "properties"
Cohesion: 0.13
Nodes (15): additionalProperties, properties, type, pattern, type, minimum, type, deploy (+7 more)

### Community 15 - "Aptabase"
Cohesion: 0.17
Nodes (11): Adding OAuth sign-in, Adding SMTP, Aptabase, Creating the first account, Custom domain, Deploy, Known limits, Marketplace listing (+3 more)

### Community 16 - "test_rt_schema.py"
Cohesion: 0.29
Nodes (9): minimal_template(), test_all_errors_are_reported_not_just_the_first(), test_duplicate_service_names_are_rejected(), test_load_template_reads_and_validates(), test_minimal_template_validates(), test_missing_name_is_rejected(), test_repo_source_requires_a_root_directory(), test_unknown_source_type_is_rejected() (+1 more)

### Community 17 - "`serializedConfig`"
Cohesion: 0.18
Nodes (10): `deploy`, `networking`, Railway template API, Reading a published template's config, `serializedConfig`, `source`, There is no `templateCreate`, Transport (+2 more)

### Community 18 - "test_rt_lint.py"
Cohesion: 0.35
Nodes (10): template_with(), test_a_clean_template_reports_nothing(), test_a_service_with_a_volume_and_no_mount_path_conflict_is_clean(), test_floating_tag_on_a_digest_pinned_registry_is_reported(), test_railway_provided_variables_are_not_treated_as_unknown(), test_reference_to_an_unknown_service_is_reported(), test_reference_to_an_unknown_variable_is_reported(), test_secret_alphabet_with_delimiters_is_reported() (+2 more)

### Community 19 - "Railway templates"
Cohesion: 0.20
Nodes (8): Development, Documentation, Railway templates, Templates, Hook-Based Usage, Installation Verification, Meta Commands (always use rtk directly), RTK - Rust Token Killer

### Community 20 - "railway.json"
Cohesion: 0.25
Nodes (7): build, builder, dockerfilePath, deploy, restartPolicyMaxRetries, restartPolicyType, $schema

### Community 26 - "variable"
Cohesion: 0.17
Nodes (12): variable, minLength, type, type, description, isOptional, value, type (+4 more)

## Knowledge Gaps
- **130 isolated node(s):** `$schema`, `$id`, `title`, `type`, `required` (+125 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 220 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `properties` connect `properties` to `$defs`, `properties`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `$defs` connect `$defs` to `template.schema.json`, `variable`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `properties` connect `template.schema.json` to `variable`, `properties`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **What connects `$schema`, `$id`, `title` to the rest of the system?**
  _130 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `template.schema.json` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Should `$defs` be split into smaller, more focused modules?**
  _Cohesion score 0.07142857142857142 - nodes in this community are weakly interconnected._
- **Should `properties` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._