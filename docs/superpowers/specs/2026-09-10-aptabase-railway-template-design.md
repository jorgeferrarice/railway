# Aptabase Railway Template — Design

Date: 2026-09-10
Status: Approved for implementation planning

## Purpose

Deliver a one-click Railway template that deploys a self-hosted
[Aptabase](https://github.com/aptabase/aptabase) instance — the open-source
Firebase/Google Analytics alternative for mobile, desktop and web apps — and publish
that template to the Railway marketplace.

This is also the first template in a new monorepo at `~/Personal/railway`, so the
design establishes the layout, tooling and conventions that later templates reuse.

## Background

Aptabase's own self-hosting setup (`aptabase/self-hosting`) is a three-container Docker
Compose stack:

| Container | Image | Role |
| --- | --- | --- |
| `aptabase` | `ghcr.io/aptabase/aptabase:main` | ASP.NET Core app + React frontend, port 8080 |
| `aptabase_db` | `postgres:15-alpine` | Relational store (accounts, apps, billing) |
| `aptabase_events_db` | `clickhouse/clickhouse-server:23.8.4.69-alpine` | Event store |

Facts established while researching, which drive several decisions below:

- The application image is built from .NET 10 (`mcr.microsoft.com/dotnet/aspnet:10.0`)
  with entrypoint `dotnet Aptabase.dll`. It has no `EXPOSE`, and relies on the ASP.NET
  container default of port 8080.
- `Program.cs` calls `RunMigrations()` before `app.Run()`. Both the PostgreSQL migrations
  and — when `CLICKHOUSE_URL` is configured — the ClickHouse migrations execute on every
  startup, before the HTTP server begins listening.
- A health endpoint exists at `/healthz` (`app.MapHealthChecks("/healthz")`).
- The GHCR repository `aptabase/aptabase` publishes only the tags `main`, `main-amd64`
  and `main-arm64`. There are no semantic version tags.
- The official ClickHouse server image ships
  `/etc/clickhouse-server/config.d/docker_related_config.xml`, which already sets
  `<listen_host>::</listen_host>`. ClickHouse therefore satisfies Railway's IPv6-only
  private networking requirement without modification.
- Railway templates have no on-disk file format. They are composed in the template editor
  or created through the GraphQL API at `https://backboard.railway.com/graphql/v2`.
- Railway CLI 5.27.2 (`railway deploy --template <code>`) can only deploy templates that
  are already published to the marketplace. It cannot deploy a local definition, and this
  CLI version has no `railway api` subcommand.

### Environment variables read by Aptabase

From `src/Features/EnvSettings.cs`:

| Variable | Required | Notes |
| --- | --- | --- |
| `BASE_URL` | Yes | Base URL used to generate links (activation emails, OAuth callbacks) |
| `AUTH_SECRET` | Yes | Random secret used to sign auth tokens |
| `DATABASE_URL` | Yes | PostgreSQL connection string, ADO.NET keyword format |
| `CLICKHOUSE_URL` | No | ClickHouse connection string; without it, event storage is disabled |
| `REGION` | No | `EU`, `US` or `SH`; defaults to `SH` (self-hosted) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS` | No | Outbound email |
| `OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET` | No | GitHub sign-in |
| `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET` | No | Google sign-in |
| `TINYBIRD_BASE_URL`, `TINYBIRD_TOKEN` | No | Aptabase Cloud only; not used here |
| `LEMONSQUEEZY_API_KEY`, `LEMONSQUEEZY_SIGNING_SECRET` | No | Aptabase Cloud billing; not used here |
| `ERROR_QUOTA_ENABLED` | No | Aptabase Cloud only; not used here |

`ConnectionStrings__postgresdb` and `ConnectionStrings__clickhousedb` override
`DATABASE_URL` and `CLICKHOUSE_URL` respectively. The template uses the plain
`*_URL` forms to stay aligned with upstream's documented setup.

## Goals

1. A Railway template that deploys a working Aptabase instance with persistent storage
   and no manual post-deploy configuration beyond creating the first account.
2. The template definition lives in version control, is reviewable as a diff, and can be
   recreated or updated from the repository rather than by hand in a browser.
3. The template is publishable to the Railway marketplace.
4. A repository structure that a second, third and fourth template can join without
   rework.

## Non-goals

- Forking or building Aptabase from source. The template consumes upstream's published
  image.
- Managing an SMTP provider, OAuth applications, or a custom domain on the deployer's
  behalf. These are documented, optional inputs.
- Migrating data from Aptabase Cloud, or any backup/restore tooling beyond what Railway's
  own volume backups provide.
- Supporting Aptabase Cloud-only features (Tinybird, LemonSqueezy billing, error quotas).

## Repository layout

```
~/Personal/railway/                       # new git monorepo
├── README.md                             # index of templates in this repo
├── RTK.md                                # copy of ~/.claude/RTK.md
├── AGENTS.md                             # caveman activation rule (via /caveman-init)
├── .cursor/rules/caveman.mdc              #   "
├── .windsurf/rules/caveman.md             #   "
├── .clinerules/caveman.md                 #   "
├── .opencode/AGENTS.md                    #   "
├── .github/copilot-instructions.md        #   "
├── graphify-out/graph.json               # knowledge graph (via /graphify .)
├── docs/superpowers/specs/               # design docs, this file included
├── schema/template.schema.json           # JSON Schema shared by every template.json
├── scripts/
│   └── railway_template.py               # introspect | validate | create | update | publish | deploy
└── templates/
    └── aptabase/
        ├── README.md                     # deploy guide + marketplace listing copy
        ├── template.json                 # the service graph
        ├── bump-digest.sh                # re-resolve the upstream image digest
        └── clickhouse/
            ├── Dockerfile
            ├── config.d/railway.xml
            └── railway.json
```

The ClickHouse service is built by Railway from a GitHub repository path
(`templates/aptabase/clickhouse`). **The monorepo must therefore be pushed to a GitHub
repository before the template can deploy.** Pushing is a separate, explicitly instructed
step; nothing in this design pushes automatically.

## Service design

Three services: `postgres`, `clickhouse`, `aptabase`.

### `postgres`

- Source: Docker image `ghcr.io/railwayapp-templates/postgres-ssl:15.19`.
- Rationale: Railway's own maintained Postgres image, which handles TLS material and
  Railway's volume conventions. Version 15 matches what Aptabase's compose file and CI
  use, so FluentMigrator runs against the major version upstream tests.
- Volume: `/var/lib/postgresql/data`.
- Variables:

  | Variable | Value |
  | --- | --- |
  | `POSTGRES_USER` | `aptabase` |
  | `POSTGRES_DB` | `aptabase` |
  | `POSTGRES_PASSWORD` | `${{secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` |
  | `PGDATA` | `/var/lib/postgresql/data/pgdata` |

- No public networking. Reached over the private network only.

The generated password alphabet is restricted to alphanumerics deliberately: the value is
interpolated into an ADO.NET connection string where `;` and `=` are delimiters, and
Railway's default `secret()` alphabet is not guaranteed to avoid them.

### `clickhouse`

- Source: GitHub repository, root directory `templates/aptabase/clickhouse`.
- Base image: `clickhouse/clickhouse-server:23.8.4.69-alpine`, pinned to the exact version
  in Aptabase's compose file so the ClickHouse migrations run against a tested server.
- Volume: `/var/lib/clickhouse`.
- Variables:

  | Variable | Value |
  | --- | --- |
  | `CLICKHOUSE_USER` | `aptabase` |
  | `CLICKHOUSE_PASSWORD` | `${{secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` |

  `CLICKHOUSE_DB` is deliberately unset. Upstream's `CLICKHOUSE_URL` carries no
  `Database=` keyword, so Aptabase writes to the `default` database. Setting
  `CLICKHOUSE_DB` would change the user's default database and silently diverge from
  upstream.

- No public networking.

A custom image rather than the stock one, because `config.d/railway.xml` adds
Railway-specific tuning that the stock image does not have:

- `max_server_memory_usage_to_ram_ratio` set to `0.7`, so ClickHouse respects the
  container memory limit instead of assuming host RAM.
- A reduced `mark_cache_size` and disabled uncompressed cache, appropriate for the small
  instances a self-hosted analytics deployment runs on.
- `trace_log`, `metric_log` and `asynchronous_metric_log` disabled, and a TTL applied to
  the remaining system log tables. Railway volumes start at 5 GB; stock ClickHouse system
  logs will consume a meaningful share of that before any events arrive.
- Logger level raised to `warning` to keep Railway's log stream readable.

It also declares `listen_host` explicitly (`::` and `0.0.0.0`, with `listen_try` left at
`1`).

This reverses an earlier decision in this document, which said the file should *not*
touch `listen_host` because the stock image's `docker_related_config.xml` already binds
`::`. That file does still set it, but implementation showed the service's entire
private-network reachability hangs on that one upstream file, which is free to change
between image versions. A custom image exists for this service anyway, so the binding is
declared here rather than inherited.

Verified on 2026-09-10 while implementing: on Docker Desktop for macOS the `::` bind
fails with `Address family for hostname not supported`, `listen_try` swallows it, and
only IPv4 comes up. That is a property of that host's disabled container IPv6, not of the
image, so the test asserts the *merged effective configuration* asks for `::` rather than
asserting a live IPv6 socket.

`railway.json` in the same directory pins the builder to Dockerfile and sets a restart
policy.

### `aptabase`

- Source: Docker image, pinned by digest:
  `ghcr.io/aptabase/aptabase@sha256:8efa3c0b451947c296410855666fb4ec8e812ddd15e4f236984284a6ad8510fe`
  (the `main` tag as resolved on 2026-09-10).
- Rationale: upstream publishes no version tags, so a digest is the only way to make a
  deploy reproducible. `bump-digest.sh` re-resolves `main` to its current digest and
  rewrites `template.json`, making every upgrade an explicit, reviewable commit.
- Public networking: HTTP domain, target port `8080`.
- Health check: path `/healthz`, timeout 300 seconds. The long timeout is required because
  `RunMigrations()` completes before the server starts listening, so a first deploy is
  unhealthy for as long as the migrations take.
- Volume: none. All state lives in the two databases.
- Variables:

  | Variable | Value |
  | --- | --- |
  | `BASE_URL` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` |
  | `AUTH_SECRET` | `${{secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` |
  | `DATABASE_URL` | `Server=${{postgres.RAILWAY_PRIVATE_DOMAIN}};Port=5432;User Id=aptabase;Password=${{postgres.POSTGRES_PASSWORD}};Database=aptabase` |
  | `CLICKHOUSE_URL` | `Host=${{clickhouse.RAILWAY_PRIVATE_DOMAIN}};Port=8123;Username=aptabase;Password=${{clickhouse.CLICKHOUSE_PASSWORD}}` |
  | `ASPNETCORE_HTTP_PORTS` | `8080` |
  | `REGION` | `SH` |
  | `SMTP_HOST` | `` (empty, optional) |
  | `SMTP_PORT` | `` (empty, optional) |
  | `SMTP_USERNAME` | `` (empty, optional) |
  | `SMTP_PASSWORD` | `` (empty, optional) |
  | `SMTP_FROM_ADDRESS` | `` (empty, optional) |
  | `OAUTH_GITHUB_CLIENT_ID` | `` (empty, optional) |
  | `OAUTH_GITHUB_CLIENT_SECRET` | `` (empty, optional) |
  | `OAUTH_GOOGLE_CLIENT_ID` | `` (empty, optional) |
  | `OAUTH_GOOGLE_CLIENT_SECRET` | `` (empty, optional) |

`ASPNETCORE_HTTP_PORTS` is set explicitly rather than left to the image default, so the
template's declared target port and the app's actual listener cannot drift apart. Kestrel
binds `http://+:8080`, which covers IPv6 and therefore works for both Railway's public
edge and private networking.

## Data flow

```
Browser ──HTTPS──▶ Railway edge ──▶ aptabase:8080
                                      │
  SDK event ingest ───────────────────┤
                                      ├──IPv6 private──▶ postgres:5432    (accounts, apps)
                                      └──IPv6 private──▶ clickhouse:8123  (events)
```

On startup, `aptabase` runs FluentMigrator against PostgreSQL and then, because
`CLICKHOUSE_URL` is set, against ClickHouse. Only after both complete does Kestrel bind
and `/healthz` start returning 200.

## Template definition and tooling

### `template.json`

A repository-owned description of the service graph — sources, variables, volumes, domains
and health checks — in a schema of our own (`schema/template.schema.json`), not Railway's
internal wire format. Keeping our own schema means the file stays readable and diffable,
and `scripts/railway_template.py` owns the translation into whatever shape the Railway API
wants.

### `scripts/railway_template.py`

Authenticates with a Railway token read from the `RAILWAY_API_TOKEN` environment variable
only. It never reads the Railway CLI's stored credentials.

Subcommands:

| Command | Behaviour |
| --- | --- |
| `validate` | Check a `template.json` against the JSON Schema. No network access. |
| `introspect` | Dump the GraphQL input types for template creation/update to stdout. |
| `create` | Create the template on the workspace from `template.json`. |
| `update` | Update an existing template in place. |
| `publish` | Publish the template to the marketplace. |
| `deploy` | Deploy the template into a project, for end-to-end verification. |

`templateCreate` and its input types are not part of Railway's documented public API, and
the schema could not be introspected during design. Implementation therefore proceeds in
two stages:

1. Ship `validate`, `introspect`, and the `template.json` → payload builder.
2. Run `introspect` against a real token, read the actual input types, and implement
   `create`, `update`, `publish` and `deploy` against them.

No GraphQL mutation is written from guesswork.

### `bump-digest.sh`

Fetches an anonymous GHCR pull token, resolves `ghcr.io/aptabase/aptabase:main` to its
current manifest-list digest, and rewrites the digest in `template.json`. Prints the old
and new digest so the upgrade is a reviewable one-line diff.

## Marketplace listing

The template is published to the Railway marketplace. `templates/aptabase/README.md`
carries the listing copy so that the published description and the repository stay in
sync:

- Name: Aptabase
- Short description: Open-source, privacy-friendly analytics for mobile, desktop and web
  apps.
- Category: Analytics
- Links: upstream repository, upstream self-hosting guide, Aptabase documentation.
- A note that the deployed instance runs `REGION=SH` and is entirely self-hosted.

Icon and banner assets are the deployer's own to supply through the Railway template
editor; this repository does not vendor Aptabase's trademarks.

## Post-deploy behaviour to document

Aptabase ships no default credentials. The first user registers through the UI, and the
activation link is delivered by email. With no SMTP configured — the default — that email
is not sent; the activation link is printed in the `aptabase` service's deploy logs
instead. `templates/aptabase/README.md` must state this prominently, with the exact steps
to find the link in Railway's log viewer, because a deployer who does not know this will
reasonably conclude the template is broken.

## Error handling and failure modes

| Failure | Cause | Mitigation |
| --- | --- | --- |
| Health check times out on first deploy | Migrations run before the listener binds | 300 s health check timeout; README explains the first boot is slower |
| `aptabase` cannot reach a database | Private domain not yet resolvable during the initial deploy race | Railway's restart policy retries; documented as expected on first deploy |
| ClickHouse OOM-killed | Server sizing itself from host RAM | `max_server_memory_usage_to_ram_ratio` in `config.d/railway.xml` |
| Volume fills up | ClickHouse system log tables | System logs disabled/TTL'd; README documents growing the volume |
| Connection string parse error | A generated secret containing `;` or `=` | Alphanumeric-only `secret()` alphabet |
| Signup appears broken | No SMTP configured | README documents the activation link in logs and how to add SMTP |

## Testing and acceptance criteria

The work is done when all of the following hold:

1. `scripts/railway_template.py validate templates/aptabase/template.json` passes.
2. `scripts/railway_template.py introspect` runs against a real token and returns the
   template input types.
3. `create` produces the template on the workspace, and the template editor shows three
   services with the variables, volumes, domain and health check described above.
4. A deploy of the template reaches a state where the Aptabase signup page loads over the
   generated public domain.
5. Registering an account produces an activation link retrievable from the `aptabase`
   deploy logs, and completing activation lands on the Aptabase dashboard.
6. `bump-digest.sh` re-resolves the digest and produces a clean one-line diff.
7. The repository baseline is satisfied: caveman rule files present, `RTK.md` at the
   repository root, and `graphify-out/graph.json` built.

Criteria 3 through 5 require deploying to a real Railway workspace, which is a billable,
outward-facing action. It happens only on explicit instruction.

## Decisions recorded

| Decision | Choice | Alternative rejected |
| --- | --- | --- |
| Deliverable shape | Source dirs + `template.json` + API script | Hand composition in the Railway UI |
| PostgreSQL | Railway `postgres-ssl:15.19` | Stock `postgres:15-alpine` (no Railway TLS/volume conventions) |
| ClickHouse | Custom image over `23.8.4.69-alpine` | Stock image (no memory or system-log tuning) |
| App image pin | Digest | `:main` (non-reproducible); mirroring with semver tags (needs CI + registry) |
| GraphQL mutations | Introspect first, then implement | Writing them from guesswork |
| SMTP | Optional, blank by default | Required at deploy time; omitted entirely |
| Marketplace | Publish | Private-by-URL |
