"""Project scaffolding operations grouped by concern."""

import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import NamedTuple


class GitAuthor(NamedTuple):
    """Git author information."""

    name: str
    email: str


def check_uv() -> None:
    """Raise SystemExit if uv is not available on PATH."""
    if shutil.which("uv") is None:
        print(
            "error: 'uv' not found on PATH.\nInstall it from https://docs.astral.sh/uv/getting-started/installation/",
            file=sys.stderr,
        )
        raise SystemExit(1)


def get_git_author() -> GitAuthor:
    """Return the git user name/email, falling back to placeholders."""
    name = ""
    email = ""
    if shutil.which("git"):
        try:
            name = subprocess.check_output(
                ["git", "config", "--get", "user.name"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except subprocess.CalledProcessError:
            pass
        try:
            email = subprocess.check_output(
                ["git", "config", "--get", "user.email"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except subprocess.CalledProcessError:
            pass
    return GitAuthor(name=name or "Your Name", email=email or "you@example.com")


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command, raising SystemExit on non-zero exit."""
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def init_project(
    project_name: str,
    python_version: str,
    cwd: Path,
    run_fn: Callable[[list[str], Path | None], None],
) -> Path:
    """Run uv init --lib and return the created project directory."""
    run_fn(["uv", "init", "--lib", "--python", python_version, project_name], cwd)
    for candidate in (project_name, project_name.replace("-", "_")):
        project_dir = cwd / candidate
        if project_dir.is_dir():
            return project_dir
    raise SystemExit(f"error: project directory not found after 'uv init' for '{project_name}'")


def write_pyproject(
    project_dir: Path,
    project_name: str,
    package_name: str,
    python_version: str,
    description: str,
    author: GitAuthor,
    default_license_id: str,
    load_template: Callable[[str], str],
    render_template: Callable[..., str],
    get_license_classifier: Callable[[str], str],
) -> None:
    """Overwrite pyproject.toml with the canonical template."""
    today = datetime.now().strftime("%Y.%m.%d")
    content = render_template(
        load_template("pyproject.toml.tmpl"),
        project_name=project_name,
        version=f"{today}.00",
        description=description,
        license_id=default_license_id,
        license_classifier=get_license_classifier(default_license_id),
        author_name=author.name,
        author_email=author.email,
        python_version=python_version,
        py_no_dot=python_version.replace(".", ""),
        package_name=package_name,
    )
    pyproject_path = project_dir / "pyproject.toml"
    pyproject_path.write_text(content, encoding="utf-8")
    print(f"Updated {pyproject_path} with project/build/tool settings.")


def create_smoke_test(
    project_dir: Path,
    package_name: str,
    load_template: Callable[[str], str],
    render_template: Callable[..., str],
) -> None:
    """Create a minimal importable smoke test."""
    tests_dir = project_dir / "src" / package_name / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    smoke_test = tests_dir / "test_smoke.py"
    content = render_template(load_template("test_smoke.py.tmpl"), package_name=package_name)
    smoke_test.write_text(content, encoding="utf-8")
    print(f"Created smoke test at {smoke_test}")


def create_venv(
    project_dir: Path,
    python_version: str,
    run_fn: Callable[[list[str], Path | None], None],
) -> None:
    """Create a virtual environment inside the project directory."""
    run_fn(["uv", "venv", "--python", python_version], project_dir)


def sync_project(
    project_dir: Path,
    run_fn: Callable[[list[str], Path | None], None],
) -> None:
    """Sync project dependencies and materialize uv.lock."""
    run_fn(
        ["uv", "sync", "--extra", "dev", "--extra", "docs", "--extra", "build"],
        project_dir,
    )
    print(f"Synced dependencies and generated lockfile in {project_dir}")


def setup_gitignore(project_dir: Path, load_template: Callable[[str], str]) -> None:
    """Create or augment .gitignore with Python-standard entries."""
    gitignore = project_dir / ".gitignore"
    template_entries = load_template("gitignore.tmpl").splitlines()
    entries = [line for line in template_entries if line]
    if not gitignore.exists():
        gitignore.write_text(load_template("gitignore.tmpl"), encoding="utf-8")
        print(f"Created {gitignore} with Python defaults.")
        return

    existing = gitignore.read_text(encoding="utf-8").splitlines()
    missing = [e for e in entries if e not in existing]
    if missing:
        with gitignore.open("a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(missing) + "\n")
        print(f"Updated {gitignore} with {len(missing)} missing Python defaults.")
    else:
        print(f"{gitignore} already contains Python defaults.")


def setup_yamllint(project_dir: Path, load_template: Callable[[str], str]) -> None:
    """Create .yamllint if it does not exist."""
    yamllint = project_dir / ".yamllint"
    if not yamllint.exists():
        yamllint.write_text(load_template("yamllint.tmpl"), encoding="utf-8")
        print(f"Created {yamllint}.")
    else:
        print(f"{yamllint} already exists, leaving it unchanged.")


def setup_vscode(project_dir: Path, load_template: Callable[[str], str]) -> None:
    """Write VS Code workspace settings."""
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings = vscode_dir / "settings.json"
    settings.write_text(load_template("vscode_settings.json.tmpl"), encoding="utf-8")
    print(f"Wrote VS Code settings to {settings}")


def setup_typos(project_dir: Path, load_template: Callable[[str], str]) -> None:
    """Create typos.toml if it does not exist."""
    typos_config = project_dir / "typos.toml"
    if not typos_config.exists():
        typos_config.write_text(load_template("typos.toml.tmpl"), encoding="utf-8")
        print(f"Created {typos_config}.")
    else:
        print(f"{typos_config} already exists, leaving it unchanged.")


def setup_justfiles(project_dir: Path, load_template: Callable[[str], str]) -> None:
    """Create a single root justfile."""
    (project_dir / "justfile").write_text(load_template("justfile.tmpl"), encoding="utf-8")
    print(f"Created justfile in {project_dir}")


def setup_docs_build_assets(
    project_dir: Path,
    package_name: str,
    load_template: Callable[[str], str],
    render_template: Callable[..., str],
) -> None:
    """Create docs and build scaffolding files."""
    docs_dir = project_dir / "docs"
    docs_sphinx_dir = project_dir / "docs_sphinx"
    docs_sphinx_static_dir = docs_sphinx_dir / "_static"
    docs_dir.mkdir(exist_ok=True)
    docs_sphinx_dir.mkdir(exist_ok=True)
    docs_sphinx_static_dir.mkdir(exist_ok=True)

    (docs_dir / "index.md").write_text(
        render_template(load_template("docs/index.md.tmpl"), package_name=package_name),
        encoding="utf-8",
    )
    (docs_dir / "python-api.md").write_text(
        render_template(load_template("docs/python-api.md.tmpl"), package_name=package_name),
        encoding="utf-8",
    )
    (docs_sphinx_dir / "conf.py").write_text(
        render_template(load_template("docs_sphinx/conf.py.tmpl"), package_name=package_name),
        encoding="utf-8",
    )
    (docs_sphinx_static_dir / "custom.css").write_text(
        load_template("docs_sphinx/custom.css.tmpl"),
        encoding="utf-8",
    )
    (project_dir / "zensical.toml").write_text(load_template("zensical.toml.tmpl"), encoding="utf-8")
    (project_dir / "build.spec").write_text(
        render_template(load_template("build.spec.tmpl"), package_name=package_name),
        encoding="utf-8",
    )
    print(f"Created docs/build scaffolding files in {project_dir}")


def infer_python_version_from_pyproject(project_dir: Path, default: str, *, strict: bool = False) -> str:
    """Infer major.minor Python version from pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        if strict:
            raise SystemExit("error: pyproject.toml not found. Run this from your project root.")
        return default

    content = pyproject.read_text(encoding="utf-8")
    match = re.search(r'(?m)^requires-python\s*=\s*">=([0-9]+\.[0-9]+)"', content)
    if match:
        return match.group(1)

    if strict:
        raise SystemExit("error: requires-python not found in pyproject.toml.")
    return default


def infer_project_name_from_pyproject(project_dir: Path, *, strict: bool = False) -> str | None:
    """Infer project.name from pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        if strict:
            raise SystemExit("error: pyproject.toml not found. Run this from your project root.")
        return None

    content = pyproject.read_text(encoding="utf-8")
    match = re.search(r'(?m)^name\s*=\s*"([^\"]+)"', content)
    if match:
        return match.group(1)

    if strict:
        raise SystemExit("error: project.name not found in pyproject.toml.")
    return None


def infer_package_name_from_pyproject(project_dir: Path, *, strict: bool = False) -> str | None:
    """Infer import package name from project.name in pyproject.toml."""
    project_name = infer_project_name_from_pyproject(project_dir, strict=strict)
    if project_name is None:
        return None
    return project_name.replace("-", "_")
