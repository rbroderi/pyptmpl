"""Command-line interface for pyptmpl."""

import argparse
import importlib.metadata
import re
import sys
import urllib.request
from functools import lru_cache
from pathlib import Path

from pyptmpl.creator_core import ci_ops
from pyptmpl.creator_core import license_ops
from pyptmpl.creator_core import project_ops
from pyptmpl.creator_core import templates

OK = 0
ERROR = 1

_SCANCODE_BASE_URL = "https://scancode-licensedb.aboutcode.org"
_SCANCODE_INDEX_URL = f"{_SCANCODE_BASE_URL}/index.json"
_PYPI_CLASSIFIERS_URL = "https://pypi.org/pypi?%3Aaction=list_classifiers"
_DEFAULT_GITHUB_ACTIONS_PYTHON = f"{sys.version_info.major}.{sys.version_info.minor}"
_DEFAULT_LICENSE_ID = "GPL-3.0-or-later"


@lru_cache(maxsize=1)
def _fetch_pypi_license_classifiers() -> list[str]:
    """Fetch License :: trove classifiers from PyPI (cached)."""
    try:
        with urllib.request.urlopen(_PYPI_CLASSIFIERS_URL, timeout=30) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(
            f"warning: could not fetch PyPI classifiers ({exc}); falling back to 'Other/Proprietary'.",
            file=sys.stderr,
        )
        return []

    return [line.strip() for line in raw.splitlines() if line.strip().startswith("License ::")]


def pick_license(project_dir: Path, python_version: str) -> None:
    try:

        def update_pyproject_license_for_selection(
            selected_project_dir: Path,
            selected_spdx_name: str,
            selected_python_version: str,
        ) -> None:
            license_ops.update_pyproject_license(
                selected_project_dir,
                selected_spdx_name,
                selected_python_version,
                lambda spdx_key: license_ops.match_pypi_classifier(
                    spdx_key,
                    _fetch_pypi_license_classifiers(),
                ),
            )

        license_ops.pick_license(
            project_dir,
            python_version,
            _SCANCODE_INDEX_URL,
            _SCANCODE_BASE_URL,
            urllib.request.urlopen,
            update_pyproject_license_for_selection,
        )
    except SystemExit as exc:
        if exc.code:
            print(str(exc), file=sys.stderr)
        raise


@lru_cache(maxsize=1)
def get_version() -> str:
    try:
        return importlib.metadata.version("pyptmpl")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyptmpl",
        description="Bootstrap a new Python project with best-practice tooling.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show program version and exit.",
    )
    parser.add_argument(
        "project_name",
        nargs="?",
        default=None,
        help="Name of the new project (prompted if not supplied).",
    )
    parser.add_argument(
        "-p",
        "--python-version",
        metavar="VERSION",
        default=None,
        help="Python version to target, e.g. 3.13 (prompted if not supplied).",
    )
    parser.add_argument(
        "-d",
        "--description",
        metavar="TEXT",
        default=None,
        help="Short project description (prompted if not supplied).",
    )
    parser.add_argument(
        "--no-license",
        action="store_true",
        help="Skip the interactive license selection step.",
    )
    parser.add_argument(
        "--no-prek",
        action="store_true",
        help="Skip prek / pre-commit setup.",
    )
    parser.add_argument(
        "--no-github-actions",
        action="store_true",
        help="Skip GitHub Actions workflow generation.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip final 'uv sync' and lockfile generation.",
    )
    parser.add_argument(
        "--github-actions-init",
        action="store_true",
        help="Create or refresh .github/dependabot.yml and workflow files in an existing project.",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory for --github-actions-init (defaults to current directory).",
    )
    return parser


def _prompt(label: str) -> str:
    """Prompt the user for a required value and strip whitespace."""
    value = input(f"{label}: ").strip()
    if not value:
        print(f"error: {label} is required.", file=sys.stderr)
        raise SystemExit(ERROR)
    return value


def _validate_python_version(value: str) -> str:
    """Validate a major.minor Python version string."""
    if re.fullmatch(r"\d+\.\d+", value):
        return value
    print(
        f"error: invalid python_version '{value}'. Expected format like 3.13.",
        file=sys.stderr,
    )
    raise SystemExit(ERROR)


def main() -> int:
    """Entry point for the pyptmpl CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    project_ops.check_uv()

    if args.github_actions_init:
        project_dir = Path(args.project_dir).resolve()
        if args.python_version:
            python_version = _validate_python_version(args.python_version)
        else:
            python_version = _validate_python_version(
                project_ops.infer_python_version_from_pyproject(
                    project_dir,
                    _DEFAULT_GITHUB_ACTIONS_PYTHON,
                    strict=True,
                )
            )
        ci_ops.setup_github_actions(
            project_dir,
            python_version,
            templates.load_template,
            templates.render_template,
        )
        return OK

    project_name: str = args.project_name or _prompt("project_name")
    python_version: str = _validate_python_version(args.python_version or _prompt("python_version"))
    description: str = args.description or _prompt("description")

    package_name = project_name.replace("-", "_")
    author = project_ops.get_git_author()

    cwd = Path.cwd()

    print(f"\nCreating project '{project_name}' (Python {python_version})…\n")

    project_dir = project_ops.init_project(project_name, python_version, cwd, project_ops.run_cmd)
    project_ops.write_pyproject(
        project_dir,
        project_name,
        package_name,
        python_version,
        description,
        author,
        _DEFAULT_LICENSE_ID,
        templates.load_template,
        templates.render_template,
        lambda spdx_key: license_ops.match_pypi_classifier(
            spdx_key,
            _fetch_pypi_license_classifiers(),
        ),
    )
    project_ops.create_smoke_test(project_dir, package_name, templates.load_template, templates.render_template)
    project_ops.create_venv(project_dir, python_version, project_ops.run_cmd)
    project_ops.setup_gitignore(project_dir, templates.load_template)
    project_ops.setup_yamllint(project_dir, templates.load_template)
    project_ops.setup_vscode(project_dir, templates.load_template)
    project_ops.setup_typos(project_dir, templates.load_template)
    project_ops.setup_justfiles(project_dir, templates.load_template)
    project_ops.setup_docs_build_assets(project_dir, package_name, templates.load_template, templates.render_template)

    if not args.no_license:
        pick_license(project_dir, python_version)

    if not args.no_prek:
        ci_ops.setup_prek(
            project_dir,
            package_name,
            python_version,
            project_ops.run_cmd,
            templates.load_template,
            templates.render_template,
        )

    if not args.no_github_actions:
        ci_ops.setup_github_actions(
            project_dir,
            python_version,
            templates.load_template,
            templates.render_template,
        )

    if not args.no_sync:
        project_ops.sync_project(project_dir, project_ops.run_cmd)

    print(f"\nBootstrap complete! Your project is ready at: {project_dir}\n")
    print("Next steps:")
    print(f"  cd {project_dir}")
    print("  uvx --from rust-just just --list")
    return OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
