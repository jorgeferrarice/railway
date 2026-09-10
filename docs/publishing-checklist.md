# Publishing checklist

`templateGenerate` damages the template it produces (see
[railway-template-api.md](railway-template-api.md)). A generated template must be
repaired in Railway's template editor before it is published. There is no
`templateUpdate` mutation, so this cannot be scripted.

## Aptabase

Stored template: `4123115a-b717-4b69-90c9-8de4a1471cbc`, code `Cg5if6`, name "Aptabase",
generated 2026-09-10 from project `80ff3381-2e5c-48b6-8416-38782d1e61f5`.

Sixteen variables came back with no value, and every variable came back required.
`templates/aptabase/template.json` is the source of truth for what they should be.

| Service | Variable | Value to restore | Optional? |
| --- | --- | --- | --- |
| postgres | `POSTGRES_USER` | `aptabase` | no |
| postgres | `POSTGRES_DB` | `aptabase` | no |
| postgres | `PGDATA` | `/var/lib/postgresql/data/pgdata` | no |
| clickhouse | `CLICKHOUSE_USER` | `aptabase` | no |
| aptabase | `ASPNETCORE_HTTP_PORTS` | `8080` | no |
| aptabase | `PORT` | `8080` | no |
| aptabase | `REGION` | `SH` | no |
| aptabase | `SMTP_HOST` | *(blank)* | yes |
| aptabase | `SMTP_PORT` | *(blank)* | yes |
| aptabase | `SMTP_USERNAME` | *(blank)* | yes |
| aptabase | `SMTP_PASSWORD` | *(blank)* | yes |
| aptabase | `SMTP_FROM_ADDRESS` | *(blank)* | yes |
| aptabase | `OAUTH_GITHUB_CLIENT_ID` | *(blank)* | yes |
| aptabase | `OAUTH_GITHUB_CLIENT_SECRET` | *(blank)* | yes |
| aptabase | `OAUTH_GOOGLE_CLIENT_ID` | *(blank)* | yes |
| aptabase | `OAUTH_GOOGLE_CLIENT_SECRET` | *(blank)* | yes |

`POSTGRES_USER` and `POSTGRES_DB` are the two that make this a correctness problem rather
than an inconvenience: `DATABASE_URL` hard-codes `User Id=aptabase;Database=aptabase`, so
a deployer who accepts the blank prompt and types anything else gets an app that cannot
reach its database.

The variables that survived generation intact — every `${{...}}` expression, including
both `${{secret(32, "...")}}` calls and every cross-service reference — need no attention.

## Then

1. Re-read the config and confirm the sixteen rows above are fixed:

```bash
.venv/bin/python scripts/railway_template.py render templates/aptabase/template.json
```

   and compare against the stored template's `serializedConfig`.
2. Publish with the marketplace metadata from
   [../templates/aptabase/README.md](../templates/aptabase/README.md):

```bash
.venv/bin/python scripts/railway_template.py publish templates/aptabase/template.json \
    --template-id 4123115a-b717-4b69-90c9-8de4a1471cbc
```

3. Add the icon and banner in the editor.
4. Delete the source project once the template no longer needs regenerating. It runs three
   services and two volumes, and bills until it is gone.
