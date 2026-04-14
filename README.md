# pypt

Bootstrap a new Python project with best-practice tooling — runnable with a single command:

```sh
uvx pypt my-project
```

`pypt` is the Python replacement for `init.ps1`. It scaffolds a fully-configured Python
project using the same conventions seen in
[Repo2xml](https://github.com/rbroderi/Repo2xml).

## Features

- Runs `uv init --lib` to create the project skeleton
- Writes an opinionated `pyproject.toml` (calver, beartype, ruff, basedpyright, ty, coverage)
- Creates a smoke test under `src/<package>/tests/`
- Creates a virtual environment via `uv venv`
- Creates `.gitignore`, `.yamllint`, and `.vscode/settings.json`
- Creates a `justfile` and `.justfiles/` sub-recipes (prek, license, github-actions, clean)
- Optionally downloads a license from [scancode-licensedb](https://scancode-licensedb.aboutcode.org/)
- Optionally installs [prek](https://github.com/rbroderi/prek) and writes `.pre-commit-config.yaml`
  with all checks from Repo2xml (ssort, ruff, basedpyright, ty, vulture, deptry, pip-audit, coverage-100, …)
- Optionally generates GitHub Actions workflows (lint-format, tests, typecheck, quality-security, publish-pypi)
  and `dependabot.yml`

## Prerequisites

- [uv](https://docs.astral.sh/uv/) on `PATH`
- [git](https://git-scm.com/) on `PATH` (optional – used to pre-fill author name/email)

## Usage

```
uvx pypt [OPTIONS] [PROJECT_NAME]

positional arguments:
  project_name          Name of the new project (prompted if omitted)

options:
  -h, --help            show this help message and exit
  -v, --version         show program version and exit
  -p VERSION, --python-version VERSION
                        Python version to target, e.g. 3.13 (prompted if omitted)
  -d TEXT, --description TEXT
                        Short project description (prompted if omitted)
  --no-license          Skip the interactive license selection step
  --no-prek             Skip prek / pre-commit setup
  --no-github-actions   Skip GitHub Actions workflow generation
```

### Examples

```sh
# Fully interactive
uvx pypt

# Supply all required values up front
uvx pypt my-lib --python-version 3.13 --description "A cool library"

# Skip optional steps
uvx pypt my-lib -p 3.13 -d "A cool library" --no-license --no-prek --no-github-actions
```

## Project structure

`pypt` keeps all its boilerplate in `src/pypt/templates/`:

```
src/pypt/templates/
├── pyproject.toml.tmpl          # pyproject.toml skeleton
├── test_smoke.py.tmpl           # smoke test
├── gitignore.tmpl               # .gitignore entries
├── yamllint.tmpl                # .yamllint config
├── vscode_settings.json.tmpl    # .vscode/settings.json
├── justfile.tmpl                # root justfile
├── justfiles/
│   ├── prek.just.tmpl           # just prek-init recipe
│   ├── license.just.tmpl        # just license recipe
│   ├── github_actions.just.tmpl # just github-actions-init recipe
│   └── clean.just.tmpl          # just clean recipe
├── pre-commit-config.yaml.tmpl  # .pre-commit-config.yaml
└── github/
    ├── dependabot.yml.tmpl
    └── workflows/
        ├── lint-format.yml.tmpl
        ├── publish-pypi.yml.tmpl
        ├── quality-security.yml.tmpl
        ├── tests.yml.tmpl
        └── typecheck.yml.tmpl
```

Template variables use `{{VARNAME}}` syntax. Add or modify templates to customise
generated output for every new project.
