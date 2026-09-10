# Aptabase

Self-hosted [Aptabase](https://github.com/aptabase/aptabase) on Railway — open-source,
privacy-friendly analytics for mobile, desktop and web apps.

## What this deploys

Three services:

| Service | Image | Role |
| --- | --- | --- |
| `aptabase` | `ghcr.io/aptabase/aptabase`, pinned by digest | The ASP.NET Core app and its React frontend, on port 8080 |
| `postgres` | `ghcr.io/railwayapp-templates/postgres-ssl:15.19` | Accounts, apps and settings |
| `clickhouse` | Built from [`clickhouse/`](clickhouse/) on `clickhouse/clickhouse-server:23.8.4.69-alpine` | Analytics events |

Both databases get a volume. The app has none — all state lives in the two databases.

The instance runs with `REGION=SH` (self-hosted). It reports nothing to Aptabase Cloud,
and no Tinybird, billing or quota integration is configured.

## Deploy

Deploy from the Railway template, or from a checkout of this repository:

```bash
export RAILWAY_API_TOKEN=...
.venv/bin/python scripts/railway_template.py apply templates/aptabase/template.json \
    --project-id <project id> --environment-id <environment id>
```

`apply` builds the services one by one with Railway's ordinary service mutations.
The `deploy` subcommand, which sends the whole definition as one `templateDeployV2`
call, is kept for the day Railway opens that mutation up; today it is refused from the
public API. See [../../docs/railway-template-api.md](../../docs/railway-template-api.md).

The first deploy is slow. Aptabase runs its PostgreSQL and ClickHouse migrations before
Kestrel starts listening, so `/healthz` stays unreachable until migrations finish. The
health check allows 300 seconds for exactly this reason.

## Creating the first account

**Aptabase ships no default credentials, and by default this template sends no email.**
Read this section before concluding the deploy is broken.

1. Open the generated public domain and register an account.
2. Aptabase generates an activation link and tries to email it. With no SMTP configured —
   the default — that email is never sent. The link is written to the app's logs instead.
3. In Railway: open the project, select the `aptabase` service, open **Deployments**,
   select the active deployment, and **View logs**. Search for the activation URL.
4. Open the link to finish activation. You land on the Aptabase dashboard.

This is expected behaviour for a self-hosted instance without SMTP, not a failed deploy.

## Adding SMTP

Set all five variables on the `aptabase` service:

| Variable | Example |
| --- | --- |
| `SMTP_HOST` | `smtp.example.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | `apikey` |
| `SMTP_PASSWORD` | your provider's password or API key |
| `SMTP_FROM_ADDRESS` | `analytics@example.com` |

Partial configuration does not work — Aptabase needs the whole set. The service restarts
when the variables change.

## Adding OAuth sign-in

Set the pair for whichever provider you want, on the `aptabase` service:

- `OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET`
- `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`

The OAuth callback URL is derived from `BASE_URL`, so register the callback against the
same origin `BASE_URL` holds.

## Custom domain

1. Add the domain to the `aptabase` service in Railway.
2. **Update `BASE_URL` to match.**

`BASE_URL` is what activation links and OAuth callbacks are built from. Leaving it on the
old Railway domain produces emails and callbacks pointing at the wrong host — a failure
that looks like broken auth rather than a stale variable.

## Upgrading

Upstream publishes no version tags — only `main` — so the app image is pinned by digest
and a bump is a deliberate jump to whatever `main` currently is. Read upstream's commits
before bumping.

```bash
.venv/bin/python scripts/railway_template.py bump templates/aptabase/template.json --service aptabase --tag main
```

Review the one-line diff and commit it. Railway has no mutation that updates a stored
template, so a published template picks the new digest up only by being regenerated from
a project built with it.

## Storage

`postgres` and `clickhouse` each mount a volume. Railway sized both at 50 GB when this
template was deployed; the default is set by your plan, not by the template, which asks
only for a mount path.

ClickHouse's high-volume system log tables (`trace_log`, `metric_log`,
`asynchronous_metric_log`, `session_log`, `text_log`, `crash_log`) are disabled in
[`clickhouse/config.d/railway.xml`](clickhouse/config.d/railway.xml), and `query_log` and
`part_log` carry a 7-day TTL. Without this, ClickHouse's own logs would claim a large
share of the volume before a single analytics event arrived.

To grow a volume, open the service in Railway, select the volume and increase its size.

## Known limits

- ClickHouse 23.8 running under Railway's memory limits is not a configuration upstream
  tests. `max_server_memory_usage_to_ram_ratio` is set to `0.7` so the server sizes itself
  from the container limit rather than host RAM, but a busy instance may still need a
  larger plan.
- The 300-second health check timeout means a genuinely broken app takes five minutes to
  report unhealthy. Check the `aptabase` deploy logs rather than waiting.
- `postgres-ssl` is Railway's image, not the plain `postgres:15-alpine` upstream's compose
  file uses. The major version matches; the TLS layer does not.

<!-- marketplace:end -->

## Marketplace listing

- **Name:** Aptabase
- **Category:** Analytics
- **Description:** Open-source, privacy-friendly analytics for mobile, desktop and web
  apps. Self-hosted, with PostgreSQL for accounts and ClickHouse for events.
- **Links:** [Source](https://github.com/aptabase/aptabase) ·
  [Self-hosting guide](https://github.com/aptabase/self-hosting) ·
  [Documentation](https://aptabase.com/docs)

Icon and banner assets are supplied through the Railway template editor. Aptabase's
trademarks are not vendored into this repository.

### Publishing is not a one-command step

A stored template comes from `templateGenerate`, which reads a deployed project — Railway
has no mutation that registers a template from a definition. Generation is lossy in two
ways that matter here:

- variable values survive only when they are `${{...}}` expressions; plain literals such
  as `PORT`, `REGION`, `POSTGRES_USER` and `POSTGRES_DB` come back with no value;
- every variable comes back required, so the nine blank-by-design `SMTP_*` and `OAUTH_*`
  variables would be forced on the deployer.

Both have to be corrected by hand in Railway's template editor before publishing, and
there is no `templateUpdate` mutation to do it from here. `template.json` remains the
source of truth for what the corrected values should be.
