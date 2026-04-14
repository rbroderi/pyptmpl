"""Project creation logic for pypt – Python port of init.ps1."""

from __future__ import annotations

import importlib.resources
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

_SCANCODE_INDEX_URL = "https://scancode-licensedb.aboutcode.org/index.json"
_SCANCODE_BASE_URL = "https://scancode-licensedb.aboutcode.org/"

_LICENSE_CLASSIFIERS: dict[str, str] = {
    "MIT": "License :: OSI Approved :: MIT License",
    "Apache-2.0": "License :: OSI Approved :: Apache Software License",
    "BSD-3-Clause": "License :: OSI Approved :: BSD License",
    "BSD-2-Clause": "License :: OSI Approved :: BSD License",
    "LGPL-3.0": "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    "LGPL-3.0-or-later": "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    "LGPL-2.1": "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
    "LGPL-2.1-or-later": "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
    "GPL-3.0": "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    "GPL-3.0-or-later": "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    "GPL-2.0": "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
    "GPL-2.0-or-later": "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
    "AGPL-3.0": "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "AGPL-3.0-or-later": "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "MPL-2.0": "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
    "ISC": "License :: OSI Approved :: ISC License (ISCL)",
    "Unlicense": "License :: Public Domain",
}

_DEFAULT_LICENSE_ID = "LGPL-3.0-or-later"
_DEFAULT_LICENSE_CLASSIFIER = _LICENSE_CLASSIFIERS[_DEFAULT_LICENSE_ID]


def _load_template(relative_path: str) -> str:
    """Load a template file from the bundled ``templates/`` directory.

    ``relative_path`` uses forward-slash separators, e.g.
    ``"github/workflows/tests.yml.tmpl"``.
    """
    resource = importlib.resources.files("pypt") / "templates"
    for part in relative_path.split("/"):
        resource = resource / part
    return resource.read_text(encoding="utf-8")


def _render(template: str, **kwargs: str) -> str:
    """Replace ``{{KEY}}`` placeholders in *template* with the given values."""
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", value)
    return template


class GitAuthor(NamedTuple):
    """Git author information."""

    name: str
    email: str


def check_uv() -> None:
    """Raise SystemExit if uv is not available on PATH."""
    if shutil.which("uv") is None:
        print(
            "error: 'uv' not found on PATH.\n"
            "Install it from https://docs.astral.sh/uv/getting-started/installation/",
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


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command, raising SystemExit on non-zero exit."""
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def init_project(project_name: str, python_version: str, cwd: Path) -> Path:
    """Run ``uv init --lib`` and return the created project directory."""
    _run(["uv", "init", "--lib", "--python", python_version, project_name], cwd=cwd)
    # uv may create the directory using the project name directly or with
    # hyphens replaced by underscores.
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
) -> None:
    """Overwrite pyproject.toml with the canonical pypt template."""
    today = datetime.now().strftime("%Y.%m.%d")
    content = _render(
        _load_template("pyproject.toml.tmpl"),
        project_name=project_name,
        version=f"{today}.00",
        description=description,
        license_id=_DEFAULT_LICENSE_ID,
        license_classifier=_DEFAULT_LICENSE_CLASSIFIER,
        author_name=author.name,
        author_email=author.email,
        python_version=python_version,
        py_no_dot=python_version.replace(".", ""),
        package_name=package_name,
    )
    pyproject_path = project_dir / "pyproject.toml"
    pyproject_path.write_text(content, encoding="utf-8")
    print(f"Updated {pyproject_path} with project/build/tool settings.")


def create_smoke_test(project_dir: Path, package_name: str) -> None:
    """Create a minimal importable smoke test."""
    tests_dir = project_dir / "src" / package_name / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    smoke_test = tests_dir / "test_smoke.py"
    content = _render(_load_template("test_smoke.py.tmpl"), package_name=package_name)
    smoke_test.write_text(content, encoding="utf-8")
    print(f"Created smoke test at {smoke_test}")


def create_venv(project_dir: Path, python_version: str) -> None:
    """Create a virtual environment inside the project directory."""
    _run(["uv", "venv", "--python", python_version], cwd=project_dir)


def setup_gitignore(project_dir: Path) -> None:
    """Create or augment .gitignore with Python-standard entries."""
    gitignore = project_dir / ".gitignore"
    template_entries = _load_template("gitignore.tmpl").splitlines()
    entries = [line for line in template_entries if line]
    if not gitignore.exists():
        gitignore.write_text(_load_template("gitignore.tmpl"), encoding="utf-8")
        print(f"Created {gitignore} with Python defaults.")
    else:
        existing = gitignore.read_text(encoding="utf-8").splitlines()
        missing = [e for e in entries if e not in existing]
        if missing:
            with gitignore.open("a", encoding="utf-8") as fh:
                fh.write("\n" + "\n".join(missing) + "\n")
            print(f"Updated {gitignore} with {len(missing)} missing Python defaults.")
        else:
            print(f"{gitignore} already contains Python defaults.")


def setup_yamllint(project_dir: Path) -> None:
    """Create .yamllint if it does not exist."""
    yamllint = project_dir / ".yamllint"
    if not yamllint.exists():
        yamllint.write_text(_load_template("yamllint.tmpl"), encoding="utf-8")
        print(f"Created {yamllint}.")
    else:
        print(f"{yamllint} already exists, leaving it unchanged.")


def setup_vscode(project_dir: Path) -> None:
    """Write VS Code workspace settings."""
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings = vscode_dir / "settings.json"
    settings.write_text(_load_template("vscode_settings.json.tmpl"), encoding="utf-8")
    print(f"Wrote VS Code settings to {settings}")


def setup_justfiles(project_dir: Path, package_name: str) -> None:
    """Create the justfile and .justfiles/ directory with all sub-recipes."""
    justfiles_dir = project_dir / ".justfiles"
    justfiles_dir.mkdir(exist_ok=True)

    (justfiles_dir / "prek.just").write_text(_load_template("justfiles/prek.just.tmpl"), encoding="utf-8")
    (justfiles_dir / "license.just").write_text(_load_template("justfiles/license.just.tmpl"), encoding="utf-8")
    (justfiles_dir / "github_actions.just").write_text(
        _load_template("justfiles/github_actions.just.tmpl"), encoding="utf-8"
    )
    (justfiles_dir / "clean.just").write_text(_load_template("justfiles/clean.just.tmpl"), encoding="utf-8")
    (project_dir / "justfile").write_text(_load_template("justfile.tmpl"), encoding="utf-8")
    print(f"Created justfile and .justfiles/ in {project_dir}")


def setup_prek(project_dir: Path, package_name: str, python_version: str) -> None:
    """Add prek to dev dependencies and write .pre-commit-config.yaml."""
    _run(["uv", "add", "--optional", "dev", "prek"], cwd=project_dir)

    py_flag = f"--py{python_version.replace('.', '')}-plus"
    content = _render(
        _load_template("pre-commit-config.yaml.tmpl"),
        python_version=python_version,
        py_flag=py_flag,
        package_name=package_name,
    )
    (project_dir / ".pre-commit-config.yaml").write_text(content, encoding="utf-8")
    print(f"Created .pre-commit-config.yaml in {project_dir}")
    _run(["uv", "run", "prek", "install"], cwd=project_dir)


def setup_github_actions(project_dir: Path, python_version: str) -> None:
    """Create .github/dependabot.yml and workflow YAML files."""
    github_dir = project_dir / ".github"
    workflows_dir = github_dir / "workflows"
    github_dir.mkdir(exist_ok=True)
    workflows_dir.mkdir(exist_ok=True)

    pv = python_version
    (github_dir / "dependabot.yml").write_text(_load_template("github/dependabot.yml.tmpl"), encoding="utf-8")
    (workflows_dir / "lint-format.yml").write_text(
        _render(_load_template("github/workflows/lint-format.yml.tmpl"), python_version=pv), encoding="utf-8"
    )
    (workflows_dir / "publish-pypi.yml").write_text(
        _render(_load_template("github/workflows/publish-pypi.yml.tmpl"), python_version=pv), encoding="utf-8"
    )
    (workflows_dir / "quality-security.yml").write_text(
        _render(_load_template("github/workflows/quality-security.yml.tmpl"), python_version=pv), encoding="utf-8"
    )
    (workflows_dir / "tests.yml").write_text(
        _render(_load_template("github/workflows/tests.yml.tmpl"), python_version=pv), encoding="utf-8"
    )
    (workflows_dir / "typecheck.yml").write_text(
        _render(_load_template("github/workflows/typecheck.yml.tmpl"), python_version=pv), encoding="utf-8"
    )
    print(f"Created GitHub automation files under {github_dir}")


def _get_license_classifier(spdx_key: str) -> str:
    """Return the PyPI trove classifier for a given SPDX license key."""
    return _LICENSE_CLASSIFIERS.get(spdx_key, "License :: Other/Proprietary License")


def _update_pyproject_license(project_dir: Path, spdx_name: str, python_version: str) -> None:
    """Patch the license field and classifiers in an existing pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        print("pyproject.toml not found, skipping pyproject license update.")
        return

    content = pyproject.read_text(encoding="utf-8")
    license_line = f'license = "{spdx_name}"'
    license_classifier = _get_license_classifier(spdx_name)
    py_ver = python_version

    # Update license field
    if re.search(r"(?m)^license\s*=", content):
        content = re.sub(r"(?m)^license\s*=.*$", license_line, content, count=1)
    else:
        content = re.sub(r"(?m)^readme\s*=.*$", r"\g<0>\n" + license_line, content, count=1)
        if license_line not in content:
            content = content.rstrip() + "\n" + license_line + "\n"

    classifiers_block = "\n".join([
        "classifiers = [",
        f'  "{license_classifier}",',
        '  "Operating System :: Microsoft :: Windows",',
        '  "Programming Language :: Python :: 3",',
        f'  "Programming Language :: Python :: {py_ver}",',
        "]",
    ])

    if re.search(r"(?ms)^classifiers\s*=\s*\[.*?^\]", content):
        content = re.sub(r"(?ms)^classifiers\s*=\s*\[.*?^\]", classifiers_block, content, count=1)
    else:
        content = re.sub(r"(?m)^requires-python\s*=.*$", r"\g<0>\n" + classifiers_block, content, count=1)
        if classifiers_block not in content:
            content = content.rstrip() + "\n" + classifiers_block + "\n"

    pyproject.write_text(content, encoding="utf-8")
    print(f"Updated {pyproject} license/classifiers for {spdx_name}")


def pick_license(project_dir: Path, python_version: str) -> None:
    """Interactively fetch, filter, and download a license from scancode-licensedb."""
    print("Fetching license index from scancode-licensedb...")
    try:
        with urllib.request.urlopen(_SCANCODE_INDEX_URL, timeout=30) as resp:  # noqa: S310
            all_licenses: list[dict[str, object]] = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not fetch license index: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    licenses = [
        lic
        for lic in all_licenses
        if not lic.get("is_exception") and not lic.get("is_deprecated") and lic.get("license")
    ]
    licenses.sort(key=lambda x: (str(x.get("spdx_license_key", "")), str(x.get("license_key", ""))))

    if not licenses:
        print("error: no licenses found in remote index.", file=sys.stderr)
        raise SystemExit(1)

    print(f"Found {len(licenses)} licenses.")
    query = input("Filter licenses by text (blank for all): ").strip()
    if query:
        filtered = [
            lic
            for lic in licenses
            if query.lower() in str(lic.get("spdx_license_key", "")).lower()
            or query.lower() in str(lic.get("license_key", "")).lower()
        ]
        if not filtered:
            print(f"error: no licenses matched filter: {query}", file=sys.stderr)
            raise SystemExit(1)
        licenses = filtered

    print(f"Showing {len(licenses)} licenses.")
    for i, lic in enumerate(licenses, 1):
        name = lic.get("spdx_license_key") or lic.get("license_key", "")
        print(f"{i}. {name}")

    selection_str = input("Enter number: ").strip()
    try:
        selection = int(selection_str)
    except ValueError:
        print("error: invalid selection.", file=sys.stderr)
        raise SystemExit(1)

    if selection < 1 or selection > len(licenses):
        print("error: selection out of range.", file=sys.stderr)
        raise SystemExit(1)

    chosen = licenses[selection - 1]
    file_name = str(chosen["license"])
    url = _SCANCODE_BASE_URL + file_name
    spdx_name = str(chosen.get("spdx_license_key") or chosen.get("license_key", file_name))

    print(f"Downloading {spdx_name}...")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            license_text = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not download license: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    (project_dir / "LICENSE").write_text(license_text, encoding="utf-8")
    print(f"Downloaded {spdx_name} to {project_dir / 'LICENSE'}")
    _update_pyproject_license(project_dir, spdx_name, python_version)
