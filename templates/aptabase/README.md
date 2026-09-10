# Deploy and Host Aptabase with Railway

[Aptabase](https://aptabase.com) is open-source, privacy-friendly analytics for mobile,
desktop and web apps. It records events without cookies, without cross-app identifiers
and without collecting personal data, and answers the questions product teams actually
ask: which versions are in use, which features get used, and where sessions end. This
template runs your own instance, so the data stays yours.

## About Hosting Aptabase

Aptabase is an ASP.NET Core application that needs two databases behind it: PostgreSQL
for accounts, apps and settings, and ClickHouse for the event stream. Hosting it means
running all three, keeping the two databases on persistent volumes, wiring the app to
them over a private network, and holding the app's port and its health check in
agreement. The app runs its own schema migrations on boot, before it starts listening,
so a first deploy is slow and a health check has to be patient. ClickHouse also needs
tuning: left stock it sizes its memory from host RAM rather than the container limit,
and its own system log tables will fill a volume before any analytics event arrives.
This template does all of that, and generates both database passwords at deploy time.

## Common Use Cases

- Product analytics for iOS, Android, macOS, Windows and Linux apps, where app-store
  privacy rules make a third-party SDK awkward.
- Web analytics for teams that need to keep event data inside their own infrastructure
  for GDPR, HIPAA or internal policy reasons.
- Release monitoring: watching adoption of a new app version and the errors that arrive
  with it.
- A self-hosted replacement for a paid analytics plan, at the cost of the containers.
- A private staging instance to develop against without polluting production analytics.

## Dependencies for Aptabase Hosting

- **PostgreSQL 15** — accounts, apps, settings and feature flags. Deployed from
  Railway's `postgres-ssl` image, on a volume.
- **ClickHouse 23.8** — the analytics event store. Built from this repository on the
  official Alpine image, with Railway-specific memory and system-log configuration, on
  a volume.
- **An SMTP server (optional)** — Aptabase signs users in by emailed link. Without SMTP
  the link is written to the deploy logs instead, which is enough to get started.
- **GitHub or Google OAuth credentials (optional)** — for social sign-in.

### Deployment Dependencies

- [Aptabase source](https://github.com/aptabase/aptabase)
- [Aptabase documentation](https://aptabase.com/docs)
- [Upstream self-hosting guide](https://github.com/aptabase/self-hosting)
- [This template's source](https://github.com/jorgeferrarice/railway/tree/main/templates/aptabase)
- [ClickHouse documentation](https://clickhouse.com/docs)

### Implementation Details

Three services. Only `aptabase` is public.

| Service | Source | Volume |
| --- | --- | --- |
| `aptabase` | `ghcr.io/aptabase/aptabase`, pinned by digest | none |
| `postgres` | `ghcr.io/railwayapp-templates/postgres-ssl:15.19` | `/var/lib/postgresql/data` |
| `clickhouse` | built from `templates/aptabase/clickhouse` on `clickhouse/clickhouse-server:23.8.4.69-alpine` | `/var/lib/clickhouse` |

**Nothing has to be configured to deploy.** Every required variable is prefilled and
every optional one is blank; all three services read "Ready to be deployed".

Both database passwords are generated per deploy with
`${{secret(32, "...")}}`, over an alphabet of letters and digits only — the passwords are
interpolated into ADO.NET connection strings, where `;` and `=` are delimiters:

```
DATABASE_URL   = Server=${{postgres.RAILWAY_PRIVATE_DOMAIN}};Port=5432;User Id=aptabase;Password=${{postgres.POSTGRES_PASSWORD}};Database=aptabase
CLICKHOUSE_URL = Host=${{clickhouse.RAILWAY_PRIVATE_DOMAIN}};Port=8123;Username=aptabase;Password=${{clickhouse.CLICKHOUSE_PASSWORD}}
```

Both use the private network. `CLICKHOUSE_URL` deliberately carries no `Database`
keyword, so events land in the default database, as upstream expects.

The user names are fixed at `aptabase` on both databases, and the PostgreSQL database
is `aptabase`, because those names are written into the connection strings above.
Changing `POSTGRES_USER`, `POSTGRES_DB` or `CLICKHOUSE_USER` without editing both
strings gives you an app that cannot reach its database.

Two port variables look redundant and are not. `ASPNETCORE_HTTP_PORTS=8080` pins
Kestrel's listener, and `PORT=8080` exists because Railway health-checks the port named
by `PORT` rather than the declared target port — Kestrel ignores `PORT`, so without it
the check probes a dead port and every deploy fails.

`aptabase` health-checks `/healthz` with the default 300-second timeout, because
FluentMigrator runs every migration before Kestrel binds. All three services restart
`ON_FAILURE` up to ten times.

Railway's private network is IPv6, so the ClickHouse image is rebuilt with a config
that listens on `::` and `0.0.0.0`, drops the high-volume system log tables
(`trace_log`, `metric_log`, `asynchronous_metric_log`, `session_log`, `text_log`,
`crash_log`), puts a 7-day TTL on `query_log` and `part_log`, and sets
`max_server_memory_usage_to_ram_ratio` to `0.7` so the server sizes itself from the
container limit.

There is no seeded administrator account. You create the first one by registering, and
without SMTP the activation link arrives in the deploy logs — see below.

### Creating the first account

**Aptabase ships no default credentials, and by default this template sends no email.**
Read this section before concluding the deploy is broken.

1. Open the generated public domain and register an account.
2. Aptabase generates an activation link and tries to email it. With no SMTP configured —
   the default — that email is never sent. The link is written to the app's logs instead.
3. In Railway: open the project, select the `aptabase` service, open **Deployments**,
   select the active deployment, and **View logs**. Search for the activation URL.
4. Open the link to finish activation. You land on the Aptabase dashboard.

This is expected behaviour for a self-hosted instance without SMTP, not a failed deploy.

### Adding SMTP

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

### Adding OAuth sign-in

Set the pair for whichever provider you want, on the `aptabase` service:

- `OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET`
- `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`

The OAuth callback URL is derived from `BASE_URL`, so register the callback against the
same origin `BASE_URL` holds.

### Custom domain

1. Add the domain to the `aptabase` service in Railway.
2. **Update `BASE_URL` to match.**

`BASE_URL` is what activation links and OAuth callbacks are built from. Leaving it on the
old Railway domain produces emails and callbacks pointing at the wrong host — a failure
that looks like broken auth rather than a stale variable.

### Upgrading

Upstream publishes no version tags — only `main` — so the app image is pinned by digest
and a bump is a deliberate jump to whatever `main` currently is. Read upstream's commits
before bumping.

```bash
.venv/bin/python scripts/railway_template.py bump templates/aptabase/template.json --service aptabase --tag main
```

Review the one-line diff and commit it. Railway has no mutation that updates a stored
template, so a published template picks the new digest up only by being regenerated from
a project built with it.

### Storage

`postgres` and `clickhouse` each mount a volume. Railway sized both at 50 GB when this
template was deployed; the default is set by your plan, not by the template, which asks
only for a mount path.

ClickHouse's high-volume system log tables (`trace_log`, `metric_log`,
`asynchronous_metric_log`, `session_log`, `text_log`, `crash_log`) are disabled in
[`clickhouse/config.d/railway.xml`](clickhouse/config.d/railway.xml), and `query_log` and
`part_log` carry a 7-day TTL. Without this, ClickHouse's own logs would claim a large
share of the volume before a single analytics event arrived.

To grow a volume, open the service in Railway, select the volume and increase its size.

### Known limits

- ClickHouse 23.8 running under Railway's memory limits is not a configuration upstream
  tests. `max_server_memory_usage_to_ram_ratio` is set to `0.7` so the server sizes itself
  from the container limit rather than host RAM, but a busy instance may still need a
  larger plan.
- The 300-second health check timeout means a genuinely broken app takes five minutes to
  report unhealthy. Check the `aptabase` deploy logs rather than waiting.
- `postgres-ssl` is Railway's image, not the plain `postgres:15-alpine` upstream's compose
  file uses. The major version matches; the TLS layer does not.
- Two warnings in the `aptabase` logs on every boot are expected and harmless.
  `Cannot load library libgssapi_krb5.so.2` is Npgsql probing for Kerberos, which the
  image does not ship and this template does not use. The ASP.NET data-protection warning
  about `/root/.aspnet/DataProtection-Keys` means those keys are not persisted, so a
  redeploy signs existing sessions out; nothing else depends on them.

### Why Deploy Aptabase on Railway?

Railway is a singular platform to deploy your infrastructure stack. Railway will host
your infrastructure so you don't have to deal with configuration, while allowing you to
vertically and horizontally scale it.

By deploying Aptabase on Railway, you are one step closer to supporting a complete
full-stack application with minimal burden. Host your servers, databases, AI agents, and
more on Railway.

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
