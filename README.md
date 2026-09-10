# Railway templates

Version-controlled [Railway](https://railway.com) template definitions.

Each template lives in `templates/<name>/` and is described by a `template.json`
validated against `schema/template.schema.json`. `scripts/railway_template.py`
turns those definitions into Railway API calls.

## Templates

| Template | Description |
| --- | --- |
| [aptabase](templates/aptabase/) | Self-hosted Aptabase — open-source analytics for mobile, desktop and web apps |

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

## Documentation

- [RTK](RTK.md)
- [Design specs](docs/superpowers/specs/)
- [Implementation plans](docs/superpowers/plans/)
