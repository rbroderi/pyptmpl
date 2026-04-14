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
_PYPI_CLASSIFIERS_URL = "https://pypi.org/pypi?%3Aaction=list_classifiers"

_DEFAULT_LICENSE_ID = "LGPL-3.0-or-later"

# Module-level cache so we only fetch the PyPI classifiers once per invocation.
_pypi_license_classifiers_cache: list[str] | None = None


def _fetch_pypi_license_classifiers() -> list[str]:
    """Fetch ``License ::`` trove classifiers from PyPI (cached)."""
    global _pypi_license_classifiers_cache  # noqa: PLW0603
    if _pypi_license_classifiers_cache is None:
        try:
            with urllib.request.urlopen(_PYPI_CLASSIFIERS_URL, timeout=30) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            print(f"warning: could not fetch PyPI classifiers ({exc}); falling back to 'Other/Proprietary'.", file=sys.stderr)
            _pypi_license_classifiers_cache = []
            return _pypi_license_classifiers_cache
        _pypi_license_classifiers_cache = [
            line.strip() for line in raw.splitlines() if line.strip().startswith("License ::")
        ]
    return _pypi_license_classifiers_cache


def _match_pypi_classifier(spdx_key: str, classifiers: list[str]) -> str:
    """Return the best-matching PyPI ``License ::`` classifier for *spdx_key*.

    Matching strategy:
    * Extract the base acronym, major version, and "or-later" flag from the
      SPDX key (e.g. ``LGPL-3.0-or-later`` → base=``LGPL``, version=``3``,
      or_later=``True``).
    * For each candidate classifier, score it:
      - +10 if the parenthetical abbreviation starts with the base acronym
        (e.g. ``(LGPLv3+)`` starts with ``LGPL``).
      - +3  if the base acronym appears as a whole word in the classifier text.
      - +1  if the base acronym appears anywhere in the text (weak signal).
      - +5  if the major version number matches.
      - -8  if the SPDX key has no version but the abbreviation has digits
        (avoids matching ``MIT-0`` when the user asked for ``MIT``).
      - +3  if or_later matches "or later" in the classifier.
      - -2  if or_later is True but the classifier lacks "or later".
      - +1  for a slight preference toward exact-version classifiers when
        or_later is False.
    * Fall back to ``License :: Other/Proprietary License`` when nothing fits.
    """
    # Special-case licenses with no natural OSI classifier
    key_lower = spdx_key.lower()
    if key_lower in ("unlicense", "cc0-1.0", "cc0"):
        for cls in classifiers:
            if "public domain" in cls.lower():
                return cls
        return "License :: Other/Proprietary License"

    base_match = re.match(r"^([A-Za-z]+)", spdx_key)
    if not base_match:
        return "License :: Other/Proprietary License"
    base = base_match.group(1).upper()

    version_match = re.search(r"(\d+)(?:\.\d+)?", spdx_key)
    version = version_match.group(1) if version_match else None

    or_later = "or-later" in key_lower or key_lower.endswith("+")

    best_cls = "License :: Other/Proprietary License"
    best_score = -1

    for cls in classifiers:
        abbrev = ""
        m = re.search(r"\(([^)]+)\)", cls)
        if m:
            abbrev = m.group(1).upper()

        score = 0
        if abbrev.startswith(base):
            score += 10
        elif re.search(r"\b" + re.escape(base) + r"\b", cls.upper()):
            score += 3
        elif base in cls.upper():
            score += 1
        else:
            continue  # no signal at all – skip

        if version:
            if re.search(r"\bV?" + re.escape(version) + r"\b", cls.upper()):
                score += 5
        else:
            # SPDX key has no version: penalise classifiers whose abbreviation
            # contains digits (e.g. avoid picking "MIT-0" for plain "MIT").
            if abbrev and re.search(r"\d", abbrev):
                score -= 8

        if or_later:
            if "or later" in cls.lower():
                score += 3
            else:
                score -= 2
        else:
            if "or later" not in cls.lower():
                score += 1

        if score > best_score:
            best_score = score
            best_cls = cls

    return best_cls


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
        license_classifier=_get_license_classifier(_DEFAULT_LICENSE_ID),
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
    """Return the best-matching PyPI trove classifier for a given SPDX license key."""
    return _match_pypi_classifier(spdx_key, _fetch_pypi_license_classifiers())


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
