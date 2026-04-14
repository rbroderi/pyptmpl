"""Command-line interface for pyptmpl."""

import argparse
import importlib.metadata
import sys
import urllib.request
from functools import lru_cache
from pathlib import Path

from pyptmpl.creator_core import ci_ops
from pyptmpl.creator_core import license_ops
from pyptmpl.creator_core import project_ops
from pyptmpl.creator_core import templates
from pyptmpl.creator_core.project_ops import GitAuthor

OK = 0
ERROR = 1

_SCANCODE_BASE_URL = "https://scancode-licensedb.aboutcode.org"
_SCANCODE_INDEX_URL = f"{_SCANCODE_BASE_URL}/index.json"
_PYPI_CLASSIFIERS_URL = "https://pypi.org/pypi?%3Aaction=list_classifiers"
_DEFAULT_GITHUB_ACTIONS_PYTHON = "3.14"
_DEFAULT_LICENSE_ID = "GPL-3.0-or-later"

_pypi_license_classifiers_cache: list[str] | None = None


def _fetch_pypi_license_classifiers() -> list[str]:
    """Fetch License :: trove classifiers from PyPI (cached)."""
    global _pypi_license_classifiers_cache  # noqa: PLW0603
    if _pypi_license_classifiers_cache is None:
        try:
            with urllib.request.urlopen(_PYPI_CLASSIFIERS_URL, timeout=30) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            print(
                f"warning: could not fetch PyPI classifiers ({exc}); falling back to 'Other/Proprietary'.",
                file=sys.stderr,
            )
            _pypi_license_classifiers_cache = []
            return _pypi_license_classifiers_cache
        _pypi_license_classifiers_cache = [
            line.strip()
            for line in raw.splitlines()
            if line.strip().startswith("License ::")
        ]
    return _pypi_license_classifiers_cache


def _load_template(relative_path: str) -> str:
    return templates.load_template(relative_path)


def _render(template: str, **kwargs: str) -> str:
    return templates.render_template(template, **kwargs)


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    project_ops.run_cmd(cmd, cwd)


def _get_license_classifier(spdx_key: str) -> str:
    return license_ops.match_pypi_classifier(
        spdx_key, _fetch_pypi_license_classifiers()
    )


def _update_pyproject_license(
    project_dir: Path, spdx_name: str, python_version: str
) -> None:
    license_ops.update_pyproject_license(
        project_dir,
        spdx_name,
        python_version,
        _get_license_classifier,
    )


def check_uv() -> None:
    project_ops.check_uv()


def get_git_author() -> GitAuthor:
    return project_ops.get_git_author()


def init_project(project_name: str, python_version: str, cwd: Path) -> Path:
    return project_ops.init_project(project_name, python_version, cwd, _run)


def write_pyproject(
    project_dir: Path,
    project_name: str,
    package_name: str,
    python_version: str,
    description: str,
    author: GitAuthor,
) -> None:
    project_ops.write_pyproject(
        project_dir,
        project_name,
        package_name,
        python_version,
        description,
        author,
        _DEFAULT_LICENSE_ID,
        _load_template,
        _render,
        _get_license_classifier,
    )


def create_smoke_test(project_dir: Path, package_name: str) -> None:
    project_ops.create_smoke_test(project_dir, package_name, _load_template, _render)


def create_venv(project_dir: Path, python_version: str) -> None:
    project_ops.create_venv(project_dir, python_version, _run)


def sync_project(project_dir: Path) -> None:
    project_ops.sync_project(project_dir, _run)


def setup_gitignore(project_dir: Path) -> None:
    project_ops.setup_gitignore(project_dir, _load_template)


def setup_yamllint(project_dir: Path) -> None:
    project_ops.setup_yamllint(project_dir, _load_template)


def setup_vscode(project_dir: Path) -> None:
    project_ops.setup_vscode(project_dir, _load_template)


def setup_typos(project_dir: Path) -> None:
    project_ops.setup_typos(project_dir, _load_template)


def setup_justfiles(project_dir: Path, package_name: str) -> None:
    del package_name
    project_ops.setup_justfiles(project_dir, _load_template)


def setup_docs_build_assets(project_dir: Path, package_name: str) -> None:
    project_ops.setup_docs_build_assets(
        project_dir, package_name, _load_template, _render
    )


def setup_prek(project_dir: Path, package_name: str, python_version: str) -> None:
    ci_ops.setup_prek(
        project_dir, package_name, python_version, _run, _load_template, _render
    )


def setup_github_actions(project_dir: Path, python_version: str) -> None:
    ci_ops.setup_github_actions(project_dir, python_version, _load_template, _render)


def infer_python_version_from_pyproject(
    project_dir: Path,
    default: str = _DEFAULT_GITHUB_ACTIONS_PYTHON,
    *,
    strict: bool = False,
) -> str:
    return project_ops.infer_python_version_from_pyproject(
        project_dir, default, strict=strict
    )


def pick_license(project_dir: Path, python_version: str) -> None:
    try:
        license_ops.pick_license(
            project_dir,
            python_version,
            _SCANCODE_INDEX_URL,
            _SCANCODE_BASE_URL,
            urllib.request.urlopen,
            _update_pyproject_license,
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


def main() -> int:
    """Entry point for the pyptmpl CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    check_uv()

    if args.github_actions_init:
        project_dir = Path(args.project_dir).resolve()
        python_version = args.python_version or infer_python_version_from_pyproject(
            project_dir, strict=True
        )
        setup_github_actions(project_dir, python_version)
        return OK

    project_name: str = args.project_name or _prompt("project_name")
    python_version: str = args.python_version or _prompt("python_version")
    description: str = args.description or _prompt("description")

    package_name = project_name.replace("-", "_")
    author = get_git_author()

    cwd = Path.cwd()

    print(f"\nCreating project '{project_name}' (Python {python_version})…\n")

    project_dir = init_project(project_name, python_version, cwd)
    write_pyproject(
        project_dir, project_name, package_name, python_version, description, author
    )
    create_smoke_test(project_dir, package_name)
    create_venv(project_dir, python_version)
    setup_gitignore(project_dir)
    setup_yamllint(project_dir)
    setup_vscode(project_dir)
    setup_typos(project_dir)
    setup_justfiles(project_dir, package_name)
    setup_docs_build_assets(project_dir, package_name)

    if not args.no_license:
        pick_license(project_dir, python_version)

    if not args.no_prek:
        setup_prek(project_dir, package_name, python_version)

    if not args.no_github_actions:
        setup_github_actions(project_dir, python_version)

    if not args.no_sync:
        sync_project(project_dir)

    print(f"\nBootstrap complete! Your project is ready at: {project_dir}\n")
    print("Next steps:")
    print(f"  cd {project_dir}")
    print("  uvx --from rust-just just --list")
    return OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
