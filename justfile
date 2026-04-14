set shell := ["powershell", "-NoProfile", "-Command"]

_default:
    @just --list

ruff:
    uvx ruff check --exclude typings
    uvx ruff format --exclude typings

# Run Python type checking with basedpyright.
typecheck:
    uvx basedpyright

# Run prek hooks against all files.
prek:
    uv run prek run --all-files; uv run prek run --all-files

test:
    uv run pytest --doctest-modules

# Run tests with coverage report.
test-cov:
    $projectNameMatch = Select-String -Path 'pyproject.toml' -Pattern '^name\s*=\s*"([^\"]+)"' -AllMatches | Select-Object -First 1; if (-not $projectNameMatch -or $projectNameMatch.Matches.Count -eq 0) { throw 'project.name not found in pyproject.toml.' }; $packageName = $projectNameMatch.Matches[0].Groups[1].Value -replace '-', '_'; uv run pytest --doctest-modules --cov=('src/' + $packageName) --cov-report=term-missing

# Build documentation site.
docs-build:
    uv sync --extra docs --extra dev
    just sphinx-build
    uv run zensical build --clean

# Serve docs locally.
docs-serve:
    uv sync --extra docs --extra dev
    just sphinx-build
    uv run zensical serve

# Generate and build API docs with Sphinx.
sphinx-build:
    if (Test-Path docs_sphinx/apidoc) { Remove-Item -Recurse -Force docs_sphinx/apidoc }
    if (Test-Path docs/api) { Remove-Item -Recurse -Force docs/api }
    $env:SPHINX_APIDOC_OPTIONS = "show-inheritance"
    $projectNameMatch = Select-String -Path 'pyproject.toml' -Pattern '^name\s*=\s*"([^\"]+)"' -AllMatches | Select-Object -First 1; if (-not $projectNameMatch -or $projectNameMatch.Matches.Count -eq 0) { throw 'project.name not found in pyproject.toml.' }; $packageName = $projectNameMatch.Matches[0].Groups[1].Value -replace '-', '_'; uv run sphinx-apidoc -f --remove-old -o docs_sphinx/apidoc ('src/' + $packageName) ('src/' + $packageName + '/tests')
    uv run sphinx-build -b html docs_sphinx docs/api

# Audit dependencies for known vulnerabilities.
pip-audit:
    uv run pip-audit .

# Build standalone executable with PyInstaller.
build:
    uv sync --extra build --extra dev
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    uv run pyinstaller build.spec
