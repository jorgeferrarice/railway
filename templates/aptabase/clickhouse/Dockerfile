# Pinned to the exact version Aptabase's own compose file uses, so the
# ClickHouse migrations run against a server upstream has tested.
FROM clickhouse/clickhouse-server:23.8.4.69-alpine

COPY config.d/railway.xml /etc/clickhouse-server/config.d/railway.xml
