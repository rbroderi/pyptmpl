"""Command-line interface for pypt."""

from __future__ import annotations

import argparse
import sys

from pypt import __version__
from pypt.creator import check_uv
from pypt.creator import create_smoke_test
from pypt.creator import create_venv
from pypt.creator import get_git_author
from pypt.creator import init_project
from pypt.creator import pick_license
from pypt.creator import setup_gitignore
from pypt.creator import setup_github_actions
from pypt.creator import setup_justfiles
from pypt.creator import setup_prek
from pypt.creator import setup_vscode
from pypt.creator import setup_yamllint
from pypt.creator import write_pyproject

OK = 0
ERROR = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pypt",
        description="Bootstrap a new Python project with best-practice tooling.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
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
    return parser


def _prompt(label: str) -> str:
    """Prompt the user for a required value and strip whitespace."""
    value = input(f"{label}: ").strip()
    if not value:
        print(f"error: {label} is required.", file=sys.stderr)
        raise SystemExit(ERROR)
    return value


def main() -> int:
    """Entry point for the pypt CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    check_uv()

    project_name: str = args.project_name or _prompt("project_name")
    python_version: str = args.python_version or _prompt("python_version")
    description: str = args.description or _prompt("description")

    package_name = project_name.replace("-", "_")
    author = get_git_author()

    import pathlib

    cwd = pathlib.Path.cwd()

    print(f"\nCreating project '{project_name}' (Python {python_version})…\n")

    project_dir = init_project(project_name, python_version, cwd)
    write_pyproject(project_dir, project_name, package_name, python_version, description, author)
    create_smoke_test(project_dir, package_name)
    create_venv(project_dir, python_version)
    setup_gitignore(project_dir)
    setup_yamllint(project_dir)
    setup_vscode(project_dir)
    setup_justfiles(project_dir, package_name)

    if not args.no_license:
        pick_license(project_dir, python_version)

    if not args.no_prek:
        setup_prek(project_dir, package_name, python_version)

    if not args.no_github_actions:
        setup_github_actions(project_dir, python_version)

    print(f"\nBootstrap complete! Your project is ready at: {project_dir}\n")
    print("Next steps:")
    print(f"  cd {project_dir}")
    print("  uvx --from rust-just just --list")
    return OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
