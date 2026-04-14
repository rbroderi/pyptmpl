# pyptmpl

Reference documentation for `pyptmpl`.

## Install

```bash
pip install pyptmpl
```

Or with uv:

```bash
uv add pyptmpl
```

## CLI quick start

```bash
# Show CLI help (if your project exposes a CLI)
python -m pyptmpl --help
```

## Python API

See [Python API](python-api.md) for import examples and advanced usage.

## Development docs

```bash
# Install docs and development dependencies
uv sync --extra docs --extra dev

# Build docs
just docs-build

# Serve docs locally
just docs-serve
```
