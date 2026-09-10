# Railway template API

Read from the live Railway GraphQL schema at `https://backboard.railway.com/graphql/v2`
on **2026-09-10**.

None of this is part of Railway's documented public API. It was obtained by
introspection and by reading the `serializedConfig` of published templates. It can change
without notice; re-run the introspection before trusting it.

## Transport

Two things about the endpoint that are not obvious and cost real debugging time:

- **Cloudflare fronts it.** A request carrying urllib's default `User-Agent` is refused
  with `HTTP 403` and a body of `error code: 1010`. The client must name itself. See
  `rt_api.USER_AGENT`.
- **Two auth schemes.** Account and team tokens use `Authorization: Bearer <token>`.
  Project tokens use `Project-Access-Token: <token>`. Sending the wrong header for the
  token in hand also yields a bare `403`.

## There is no `templateCreate`

The spec assumed a `templateCreate` / `templateUpdate` pair. Neither exists. The complete
set of template mutations is:

| Mutation | Signature |
| --- | --- |
| `templateGenerate` | `(input: TemplateGenerateInput) -> Template` |
| `templateDeployV2` | `(input: TemplateDeployV2Input) -> TemplateDeployPayload` |
| `templatePublish` | `(id: String, input: TemplatePublishInput) -> Template` |
| `templateUnpublish` | `(id: String) -> Boolean` |
| `templateDelete` | `(id: String, input: TemplateDeleteInput) -> Boolean` |
| `templateClone` | `(input: TemplateCloneInput) -> Template` |
| `templateRevert` | `(input: TemplateRevertInput) -> TemplateDeployPayload` |
| `templateServiceSourceEject` | `(input: TemplateServiceSourceEjectInput) -> Boolean` |
| `templateVolumeUpdate` | `(serviceId, sizeMB, templateId, volumeId) -> Template` |
| `sandboxTemplateBuild` | `(environmentId: String, input: SandboxTemplateInput)` |

Input types:

```
TemplateGenerateInput   { environmentId, projectId }
TemplateDeployV2Input   { environmentId, existingRootServiceId, projectId,
                          serializedConfig, stageOnly, templateId, workspaceId }
TemplatePublishInput    { category, demoProjectId, description, image, readme, workspaceId }
TemplateCloneInput      { code, workspaceId }
```

`templateGenerate` takes only a project and environment. **A template is generated from a
deployed project, not authored from a definition.** This inverts the workflow the spec
described:

1. `templateDeployV2` with an inline `serializedConfig` deploys a definition into a
   project. No stored template is needed.
2. `templateGenerate` turns that deployed project into a stored `Template`.
3. `templatePublish` publishes it, carrying the marketplace metadata (`category`,
   `description`, `image`, `readme`).

Step 1 creates real, billable infrastructure. There is no way to register a template from
a definition without deploying it first.

## `templateDeployV2` is refused from the public API

Verified on 2026-09-10 by bisection. Every call returns
`HTTP 400 {"message":"Problem processing request"}`, with no detail, for:

- our own `serializedConfig`, from a full three-service config down to a single
  service with nothing but a name and an image;
- `serializedConfig` sent as a JSON object and as a JSON string;
- Railway's own published `postgres` template by `templateId`, with no config of ours
  involved at all;
- every combination of `projectId`, `environmentId` and `workspaceId`, with and without
  `stageOnly`.

Meanwhile `serviceCreate`, `variableCollectionUpsert`, `volumeCreate`,
`serviceDomainCreate` and `serviceInstanceUpdate` all succeed with the same token in the
same project, and `query { me { id } }` resolves. The token is a valid account token; the
mutation itself is not available.

`scripts/rt_apply.py` therefore builds services with the ordinary service mutations, and
the template is produced from the finished project with `templateGenerate`.

## What `templateGenerate` drops

**A generated template is not a faithful copy of the project it came from.** Verified on
2026-09-10 against a project built from `templates/aptabase/template.json`:

1. **Plain literal variable values are discarded.** `defaultValue` survives only when the
   value is a `${{...}}` expression — a reference like
   `${{postgres.RAILWAY_PRIVATE_DOMAIN}}` or a function like `${{secret(32, "...")}}`.
   Literals are emitted as `{"isOptional": false}` with no `defaultValue` at all.

   Lost in our case: `PGDATA`, `POSTGRES_DB`, `POSTGRES_USER`, `CLICKHOUSE_USER`,
   `PORT`, `REGION`, `ASPNETCORE_HTTP_PORTS`.

2. **`isOptional` is reset to `false` for everything.** The nine blank-by-design `SMTP_*`
   and `OAUTH_*` variables all come back required.

Together these turn a deployable definition into one with roughly thirteen blank required
fields, including `POSTGRES_USER` and `POSTGRES_DB` — which the connection strings
hard-code as `aptabase`, so a deployer who types anything else gets an app that cannot
reach its database.

There is no `templateUpdate` mutation, so this **cannot be repaired through the API**. The
variables have to be corrected in Railway's template editor before the template is fit to
publish.

The good news, since it was the main worry going in: `${{secret(32, "...")}}` survives
generation intact. Railway keeps the generator expression rather than the value it
expanded to when the project was built, so a published template does not ship a fixed
password.

## `serializedConfig`

`SerializedTemplateConfig` is a **custom scalar** — an opaque JSON blob. Its shape cannot
be introspected. What follows was reverse-engineered from the `serializedConfig` of 37
services across published templates (`postgres`, the `clickhouse*` family, the `umami*`
family).

```jsonc
{
  "services": {
    "<service uuid>": {
      "name": "Postgres",
      "icon": "https://devicons.railway.app/i/postgresql.svg",
      "build": {},
      "source": { "image": "ghcr.io/railwayapp-templates/postgres-ssl:18" },
      "variables": {
        "POSTGRES_USER": {
          "isOptional": false,
          "description": "User to connect to Postgres DB",
          "defaultValue": "postgres"
        }
      },
      "deploy": { "requiredMountPath": "/var/lib/postgresql/data" },
      "networking": {},
      "volumeMounts": {
        "<volume uuid>": { "mountPath": "/var/lib/postgresql/data" }
      }
    }
  }
}
```

Service keys are UUIDs generated by the author, not service names. The display name lives
in `name`.

### `source`

Two forms, observed 19 image / 18 repo across the sample:

```jsonc
{ "image": "ghcr.io/owner/name:tag" }

{ "repo": "railwayapp-templates/clickhouse-cluster",
  "branch": null,                       // null is accepted; means the default branch
  "rootDirectory": "/clickhouse_keeper" }  // note the leading slash
```

### `variables`

Keyed by variable name. Note the field is **`defaultValue`**, not `value`:

```jsonc
{ "isOptional": false, "description": "...", "defaultValue": "..." }
```

Template variable functions appear inside `defaultValue`, e.g.
`${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}`, and
cross-service references as `${{RAILWAY_PRIVATE_DOMAIN}}` or `${{POSTGRES_DB}}`.

### `deploy`

Only these keys were observed across the sample:

| Key | Count |
| --- | --- |
| `healthcheckPath` | 25 |
| `startCommand` | 19 |
| `restartPolicyType` | 12 |
| `restartPolicyMaxRetries` | 12 |
| `requiredMountPath` | 2 |

**`healthcheckTimeout` is not among them.** It exists on `ServiceInstanceUpdateInput`
(alongside `healthcheckPath`, `restartPolicyType`, `rootDirectory`, `startCommand` and
others), so it is settable on a deployed service — but it cannot be carried by a template.
See the consequence noted in the design spec.

### `networking`

```jsonc
{
  "serviceDomains": { "<hasDomain>:8080": { "port": 8080 } },
  "tcpProxies": { "9000": {} }
}
```

`<hasDomain>` is a literal magic key, not a placeholder to substitute. An empty
`networking: {}` means the service is private.

### `volumeMounts`

Keyed by volume UUID, value `{ "mountPath": "/path" }`. A service with a volume also
carries `deploy.requiredMountPath` with the same path.

## Reading a published template's config

Useful for checking a change against how Railway's own templates express something:

```graphql
query($code: String!) { template(code: $code) { name code serializedConfig } }
```

`templateSearch` returns `TemplateSearchResult`, which does **not** expose
`serializedConfig` — search for the code first, then fetch the template by code.
