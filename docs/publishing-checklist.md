# Publishing checklist

Railway has no mutation that registers a template from a definition. A stored template is
always produced by `templateGenerate` from a project that already exists, and generation
is lossy. This is the list of what has to be repaired afterwards, and where.

## What generation loses

See [railway-template-api.md](railway-template-api.md) for the evidence. In short:

- **plain literal variable values.** `defaultValue` survives only for `${{...}}`
  expressions — references and functions. A literal comes back with no value at all.
- **`isOptional`.** Every variable comes back required.
- **descriptions.** Every variable comes back with none.

Cross-service references, `${{secret(...)}}` calls, image digests, repository sources and
root directories, health-check paths, restart policies, volumes and the generated domain
all survive intact.

None of this can be repaired through the API — there is no `templateUpdate` mutation. It
is fixed in Railway's template editor, at
`https://railway.com/workspace/templates/<template id>`, one variable at a time through
each row's ⋮ → Edit. That form carries the value, the description and a "Mark as optional"
checkbox, which is the whole repair. Edits stage until you press Apply.

`templates/<name>/template.json` is the source of truth for what every field should be.

## Verifying the repair

```bash
export RAILWAY_API_TOKEN=...
.venv/bin/python - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import rt_api
q = "query($id: String!) { template(id: $id) { serializedConfig } }"
cfg = rt_api.graphql(q, {"id": "<template id>"})["template"]["serializedConfig"]
for service in cfg["services"].values():
    for name, v in (service.get("variables") or {}).items():
        if v.get("defaultValue") is None and not v.get("isOptional"):
            print("blank and required:", service["name"], name)
PY
```

Silence means the template no longer demands anything the deployer cannot supply. The
deploy page itself is the other check: every service should read **Ready to be deployed**
before you press Deploy.

## The overview's shape is mandated

Railway's [template best practices](https://docs.railway.com/templates/best-practices#overview)
prescribe the readme's skeleton, and a template published without it reads as
incomplete:

```
# Deploy and Host [X] with Railway        ~50 words on what X is
## About Hosting [X]                      ~100 words on what hosting it involves
## Common Use Cases                       3-5 bullets
## Dependencies for [X] Hosting           what else the template runs
### Deployment Dependencies               external links
### Implementation Details                optional
### Why Deploy [X] on Railway?            Railway's own closing copy
```

`tests/test_aptabase_template.py::TestMarketplaceOverview` asserts these headings
are present, in that order, in the readme `build_publish_input` actually sends.

The same page carries the rest of the checklist worth reading before publishing
anything: 1:1 transparent icons, brand-accurate service names, private networking,
a description on every variable, generated rather than hardcoded secrets, health
checks, and volumes on every stateful service.

## Aptabase

Repaired and verified on 2026-09-10. Template `4123115a-b717-4b69-90c9-8de4a1471cbc`,
code `Cg5if6`, deploy page <https://railway.com/deploy/Cg5if6>.

Sixteen variables were repaired: `POSTGRES_USER`, `POSTGRES_DB`, `PGDATA`,
`CLICKHOUSE_USER`, `PORT`, `REGION` and `ASPNETCORE_HTTP_PORTS` had their values
restored; the five `SMTP_*` and four `OAUTH_*` variables were marked optional. All
twenty-two carry their descriptions again.

`POSTGRES_USER` and `POSTGRES_DB` were the two that mattered most: `DATABASE_URL`
hard-codes `User Id=aptabase;Database=aptabase`, so a deployer who accepted the blank
prompt and typed anything else would have got an app that could not reach its database.

### Marketplace listing

Blocked. `templatePublish` answers:

> You have been blocked from publishing templates. Please reach out to the team for
> more information.

That is an account restriction, and it needs Railway support to lift. The template is
fully usable in the meantime through its deploy link — publishing adds the marketplace
listing (discovery, description, readme, icon, usage kickback), not the ability to deploy.

Two best-practice gaps are outstanding, both cosmetic and both needing a decision:

- **Service names are lowercase** — `postgres`, `clickhouse`, `aptabase`. Railway asks
  for brand-accurate names (`PostgreSQL`, `ClickHouse`, `Aptabase`). Renaming means
  editing the two connection strings as well, since reference variables address services
  by name, and re-verifying a deploy.
- **No icons.** The template and each service want a 1:1 logo with a transparent
  background, added through the editor. Aptabase's marks are not vendored into this
  repository.

Once it is lifted:

```bash
.venv/bin/python scripts/railway_template.py publish templates/aptabase/template.json \
    --template-id 4123115a-b717-4b69-90c9-8de4a1471cbc
```

Railway's CLI can do the same thing — `railway templates publish <id> --category
Analytics --description "..." --readme-file README.md`, with `railway templates update`
as the alias for replacing that metadata afterwards. Note that `update` replaces the
listing metadata only; neither the CLI nor the API can change a stored template's
`serializedConfig`.

Then add the icon and banner in the editor. `build_publish_input` already rewrites the
readme's relative links against `repository` and cuts it at `<!-- marketplace:end -->`,
so the marketplace page gets a readme that stands on its own.
