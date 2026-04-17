set shell := ["sh", "-cu"]
set windows-shell := ["powershell", "-NoProfile", "-Command"]

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
    uv run prek run --all-files

test:
    uv run pytest --doctest-modules --ignore=docs_sphinx

# Run tests with coverage report.
test-cov:
    uv run python -c "import pathlib,tomllib,pytest; data=tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')); name=data.get('project', {}).get('name'); assert isinstance(name, str), 'project.name not found in pyproject.toml.'; p=name.replace('-', '_'); raise SystemExit(pytest.main(['--doctest-modules', '--ignore=docs_sphinx', f'--cov=src/{p}', '--cov-report=term-missing']))"

# Run mutation testing on the package source.
mutate:
    uv run python -c "import pathlib,tomllib,subprocess,sys; data=tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')); name=data.get('project', {}).get('name'); assert isinstance(name, str), 'project.name not found in pyproject.toml.'; p=name.replace('-', '_'); raise SystemExit(subprocess.call(['uvx','--from','fest-mutate','fest','run','--source',f'src/{p}/**/*.py','--exclude',f'src/{p}/tests/**/*.py','--filter-operators','!constant_replace','--filter-operators','!return_value','--filter-operators','!break_continue','--filter-operators','!augmented_assign','--fail-under','100']))"

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
    uv run python -c "import os,pathlib,tomllib,shutil,subprocess; shutil.rmtree('docs_sphinx/apidoc', ignore_errors=True); shutil.rmtree('docs/api', ignore_errors=True); data=tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')); name=data.get('project', {}).get('name'); assert isinstance(name, str), 'project.name not found in pyproject.toml.'; p=name.replace('-', '_'); env=dict(os.environ); env['SPHINX_APIDOC_OPTIONS']='show-inheritance'; subprocess.check_call(['uv','run','sphinx-apidoc','-f','--remove-old','-o','docs_sphinx/apidoc',f'src/{p}',f'src/{p}/tests'], env=env); subprocess.check_call(['uv','run','sphinx-build','-b','html','docs_sphinx','docs/api'])"

# Audit dependencies for known vulnerabilities.
pip-audit:
    uv run pip-audit .

# Build standalone executable with PyInstaller.
build:
    uv sync --extra build --extra dev
    uv run python -c "import shutil; shutil.rmtree('build', ignore_errors=True); shutil.rmtree('dist', ignore_errors=True)"
    uv run pyinstaller build.spec
