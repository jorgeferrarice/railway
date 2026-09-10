# Graph Report - railway  (2026-09-10)

## Corpus Check
- 33 files · ~22,164 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 500 nodes · 657 edges · 27 communities
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9f991d77`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- properties
- template.schema.json
- properties
- bump_digest.py
- Aptabase Railway Template — Design
- test_aptabase_template.py
- railway_template.py
- Aptabase Railway Template Implementation Plan
- test_rt_api.py
- rt_api.py
- test_bump_digest.py
- test_rt_schema.py
- test_clickhouse_image.py
- variable
- test_rt_payload.py
- Aptabase
- test_rt_apply.py
- test_rt_lint.py
- Railway templates
- railway.json
- rt_payload.py
- test_railway_template_cli.py

## God Nodes (most connected - your core abstractions)
1. `template_with()` - 21 edges
2. `Aptabase Railway Template Implementation Plan` - 18 edges
3. `only_service()` - 14 edges
4. `Aptabase Railway Template — Design` - 14 edges
5. `template_with()` - 13 edges
6. `apply()` - 13 edges
7. `build_parser()` - 12 edges
8. `graphql()` - 12 edges
9. `Aptabase` - 11 edges
10. `fake_transport()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `_create_domain()` --calls--> `graphql()`  [INFERRED]
  scripts/rt_apply.py → scripts/rt_api.py
- `_create_service()` --calls--> `graphql()`  [INFERRED]
  scripts/rt_apply.py → scripts/rt_api.py
- `_create_volumes()` --calls--> `graphql()`  [INFERRED]
  scripts/rt_apply.py → scripts/rt_api.py
- `_set_variables()` --calls--> `graphql()`  [INFERRED]
  scripts/rt_apply.py → scripts/rt_api.py
- `_update_instance()` --calls--> `graphql()`  [INFERRED]
  scripts/rt_apply.py → scripts/rt_api.py

## Import Cycles
- None detected.

## Communities (27 total, 0 thin omitted)

### Community 0 - "properties"
Cohesion: 0.08
Nodes (27): minLength, type, additionalProperties, properties, $ref, required, type, minLength (+19 more)

### Community 1 - "template.schema.json"
Cohesion: 0.06
Nodes (35): additionalProperties, minLength, type, $defs, imageSource, repoSource, service, $id (+27 more)

### Community 2 - "properties"
Cohesion: 0.05
Nodes (39): $ref, additionalProperties, properties, type, pattern, type, minimum, type (+31 more)

### Community 3 - "bump_digest.py"
Cohesion: 0.10
Nodes (18): bump(), current_image(), DigestResolutionError, _HeadRequest, Path, RuntimeError, Re-resolve a digest-pinned image to the current digest behind its tag., Raised when a digest cannot be resolved or applied. (+10 more)

### Community 4 - "Aptabase Railway Template — Design"
Cohesion: 0.08
Nodes (24): `aptabase`, Aptabase Railway Template — Design, Background, `bump-digest.sh`, `clickhouse`, Correction: step 1 does not work either, Correction: `templateGenerate` is lossy, Correction: there is no `templateCreate` (+16 more)

### Community 5 - "test_aptabase_template.py"
Cohesion: 0.09
Nodes (5): fixture, Railway health-checks the port named by PORT, not the target port. Kestrel is…, services(), template(), test_port_is_pinned_so_health_checks_probe_the_right_port()

### Community 6 - "railway_template.py"
Cohesion: 0.13
Nodes (24): ArgumentParser, build_parser(), cmd_apply(), cmd_bump(), cmd_deploy(), cmd_generate(), cmd_introspect(), cmd_lint() (+16 more)

### Community 7 - "Aptabase Railway Template Implementation Plan"
Cohesion: 0.10
Nodes (19): Aptabase Railway Template Implementation Plan, Deviation from the spec, File Structure, Global Constraints, Self-Review, Task 10: Create, update, publish and deploy subcommands, Task 11: Template README and marketplace listing, Task 12: Push the repository to GitHub (+11 more)

### Community 8 - "test_rt_api.py"
Cohesion: 0.15
Nodes (12): fake_transport(), FakeResponse, Cloudflare fronts the Railway API and answers urllib's default User-Agent with…, test_a_project_token_uses_the_project_access_token_header(), test_describe_type_raises_for_an_unknown_type(), test_describe_type_returns_the_input_fields(), test_find_mutations_filters_case_insensitively(), test_graphql_identifies_this_client_by_user_agent() (+4 more)

### Community 9 - "rt_api.py"
Cohesion: 0.12
Nodes (25): HTTPError, describe_type(), _error_body(), find_mutations(), get_token(), graphql(), MissingTokenError, RuntimeError (+17 more)

### Community 10 - "test_bump_digest.py"
Cohesion: 0.21
Nodes (12): fake_registry(), FakeResponse, template_file(), test_bump_is_a_no_op_when_the_digest_is_unchanged(), test_bump_preserves_the_rest_of_the_file_byte_for_byte(), test_bump_rejects_a_service_that_is_not_digest_pinned(), test_bump_rewrites_the_digest_in_place(), test_current_image_raises_for_an_unknown_service() (+4 more)

### Community 11 - "test_rt_schema.py"
Cohesion: 0.11
Nodes (22): _duplicate_service_errors(), load_schema(), load_template(), Path, Load and validate Railway template definitions., Raised when a template definition does not match the schema., Read the template JSON Schema from disk., Raise TemplateValidationError if the template does not match the schema.… (+14 more)

### Community 12 - "test_clickhouse_image.py"
Cohesion: 0.19
Nodes (11): fixture, query(), Do not depend on upstream's docker_related_config.xml for this. It is…, Assert the merged config, not a live socket. Whether the "::" bind succeeds…, running_clickhouse(), strip_xml_comments(), test_it_answers_queries_for_the_configured_user(), test_memory_is_sized_from_the_container_limit() (+3 more)

### Community 13 - "variable"
Cohesion: 0.17
Nodes (12): variable, minLength, type, type, description, isOptional, value, type (+4 more)

### Community 14 - "test_rt_payload.py"
Cohesion: 0.12
Nodes (26): aptabase_config(), only_service(), fixture, serializedConfig has no healthcheckTimeout field. Railway reads the timeout…, Cross-service references resolve by service name, so it must match exactly what…, template_with(), test_a_private_service_has_empty_networking(), test_a_repo_source_gets_a_leading_slash_on_the_root_directory() (+18 more)

### Community 15 - "Aptabase"
Cohesion: 0.08
Nodes (24): `deploy`, `networking`, Railway template API, Reading a published template's config, `serializedConfig`, `source`, `templateDeployV2` is refused from the public API, There is no `templateCreate` (+16 more)

### Community 16 - "test_rt_apply.py"
Cohesion: 0.17
Nodes (19): api(), apply(), FakeAPI, fixture, Records every mutation and answers with plausible ids., A variable like ${{db.PASSWORD}} cannot resolve until db exists, so every…, template_with(), test_a_private_service_gets_no_domain() (+11 more)

### Community 18 - "test_rt_lint.py"
Cohesion: 0.19
Nodes (16): _lint_image(), _lint_references(), _lint_secrets(), lint_template(), Checks on template definitions that the JSON Schema cannot express., Return every problem found in the template. Empty list means clean., template_with(), test_a_clean_template_reports_nothing() (+8 more)

### Community 19 - "Railway templates"
Cohesion: 0.20
Nodes (8): Development, Documentation, Railway templates, Templates, Hook-Based Usage, Installation Verification, Meta Commands (always use rtk directly), RTK - Rust Token Killer

### Community 20 - "railway.json"
Cohesion: 0.25
Nodes (7): build, builder, dockerfilePath, deploy, restartPolicyMaxRetries, restartPolicyType, $schema

### Community 26 - "rt_payload.py"
Cohesion: 0.17
Nodes (17): build_deploy_input(), build_publish_input(), build_serialized_config(), _deploy(), _networking(), Translate a template.json into Railway's serializedConfig payload.…, Build the TemplateDeployV2Input for this template., Build the TemplatePublishInput carrying the marketplace metadata. (+9 more)

### Community 27 - "test_railway_template_cli.py"
Cohesion: 0.11
Nodes (3): fixture, Record GraphQL calls and answer them, so no test reaches the network., recorded()

## Knowledge Gaps
- **134 isolated node(s):** `$schema`, `$id`, `title`, `type`, `required` (+129 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 268 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `properties` connect `properties` to `template.schema.json`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `$defs` connect `template.schema.json` to `variable`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `properties` connect `properties` to `template.schema.json`, `properties`, `variable`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `$schema`, `$id`, `title` to the rest of the system?**
  _134 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `properties` be split into smaller, more focused modules?**
  _Cohesion score 0.08262108262108261 - nodes in this community are weakly interconnected._
- **Should `template.schema.json` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._
- **Should `properties` be split into smaller, more focused modules?**
  _Cohesion score 0.05128205128205128 - nodes in this community are weakly interconnected._