"""License matching, pyproject patching, and interactive license selection."""

import json
import re
import shutil
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import cast

import beaupy


def _beaupy_api() -> Any:
    return cast(Any, beaupy)


def _run_with_beaupy_interrupts(action: Callable[[], Any]) -> Any:
    api = _beaupy_api()
    config = getattr(api, "Config", None)
    if config is None or not hasattr(config, "raise_on_interrupt"):
        return action()

    previous = bool(config.raise_on_interrupt)
    config.raise_on_interrupt = True
    try:
        return action()
    finally:
        config.raise_on_interrupt = previous


def match_pypi_classifier(spdx_key: str, classifiers: list[str]) -> str:
    """Return the best-matching PyPI License :: classifier for an SPDX key."""
    key_lower = spdx_key.lower()
    if key_lower in ("unlicense", "cc0-1.0", "cc0"):
        for cls in classifiers:
            if "public domain" in cls.lower():
                return cls
        return "License :: Other/Proprietary License"

    base_token = re.split(r"[-+]", spdx_key, maxsplit=1)[0]
    base = "".join(ch for ch in base_token if ch.isalnum()).upper()
    if not base:
        return "License :: Other/Proprietary License"

    alt_base = base.lstrip("0123456789")
    base_candidates = [base]
    if alt_base and alt_base != base:
        base_candidates.append(alt_base)

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
        cls_upper = cls.upper()
        matched = False
        for candidate in base_candidates:
            if abbrev.startswith(candidate):
                score += 10
                matched = True
                break
            if re.search(r"\b" + re.escape(candidate) + r"\b", cls_upper):
                score += 3
                matched = True
                break
            if candidate in cls_upper:
                score += 1
                matched = True
                break
        if not matched:
            continue

        if version:
            if re.search(r"\bV?" + re.escape(version) + r"\b", cls_upper):
                score += 5
        elif abbrev and re.search(r"\d", abbrev):
            score -= 8

        if or_later:
            if "or later" in cls.lower():
                score += 3
            else:
                score -= 2
        elif "or later" not in cls.lower():
            score += 1

        if score > best_score:
            best_score = score
            best_cls = cls

    return best_cls


def _replace_project_scalar(section: list[str], key: str, value: str) -> list[str]:
    line = f'{key} = "{value}"'
    for idx, current in enumerate(section):
        if current.strip().startswith(f"{key} ="):
            section[idx] = line
            return section
    section.append(line)
    return section


def _replace_project_classifiers(section: list[str], classifiers: list[str]) -> list[str]:
    out: list[str] = []
    in_classifiers = False
    for line in section:
        stripped = line.strip()
        if stripped.startswith("classifiers = ["):
            in_classifiers = True
            continue
        if in_classifiers:
            if stripped == "]":
                in_classifiers = False
            continue
        out.append(line)

    block = [
        "classifiers = [",
        *[f'  "{item}",' for item in classifiers],
        "]",
    ]

    insert_at = len(out)
    for idx, line in enumerate(out):
        if line.strip().startswith("requires-python ="):
            insert_at = idx + 1
            break
    return out[:insert_at] + block + out[insert_at:]


def update_pyproject_license(
    project_dir: Path,
    spdx_name: str,
    python_version: str,
    get_license_classifier: Callable[[str], str],
) -> None:
    """Patch license and classifier block in an existing pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        print("pyproject.toml not found, skipping pyproject license update.")
        return

    content = pyproject.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        print("invalid pyproject.toml, skipping pyproject license update.")
        return

    project = data.get("project")
    if not isinstance(project, dict):
        print("[project] table not found, skipping pyproject license update.")
        return

    lines = content.splitlines()
    start = -1
    end = len(lines)
    for idx, line in enumerate(lines):
        if line.strip() == "[project]":
            start = idx
            break
    if start == -1:
        print("[project] table not found, skipping pyproject license update.")
        return

    for idx in range(start + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = idx
            break

    license_classifier = get_license_classifier(spdx_name)
    classifiers = [
        license_classifier,
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        f"Programming Language :: Python :: {python_version}",
    ]

    project_section = lines[start + 1 : end]
    project_section = _replace_project_scalar(project_section, "license", spdx_name)
    project_section = _replace_project_classifiers(project_section, classifiers)

    updated = lines[: start + 1] + project_section + lines[end:]
    pyproject.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
    print(f"Updated {pyproject} license/classifiers for {spdx_name}")


def _can_use_beaupy() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _prompt_text(prompt: str) -> str:
    if _can_use_beaupy():
        value = _run_with_beaupy_interrupts(lambda: _beaupy_api().prompt(prompt))
        if value is None:
            return ""
        return str(value).strip()
    return input(prompt).strip()


def _beaupy_license_page_size() -> int:
    """Choose a page size that fits short terminals without scrolling."""
    # Keep the selection menu compact enough to fit in common small terminal windows.
    terminal_lines = shutil.get_terminal_size(fallback=(80, 24)).lines
    # Reserve space for contextual prints, prompt chrome, and breathing room.
    available_option_rows = max(4, terminal_lines - 8)
    # Budget for Back/Prev/Next rows so navigation controls remain visible.
    max_license_rows = available_option_rows - 3
    return max(1, min(12, max_license_rows))


def _select_license_with_back(
    licenses: list[dict[str, object]],
) -> dict[str, object] | None:
    print(f"Showing {len(licenses)} licenses.")

    if _can_use_beaupy():
        page_size = _beaupy_license_page_size()
        total_pages = max(1, (len(licenses) + page_size - 1) // page_size)
        page_index = 0

        while True:
            start = page_index * page_size
            end = start + page_size
            page_licenses = licenses[start:end]

            options: list[str] = ["< Back to filter >"]
            option_kinds: list[tuple[str, int | None]] = [("back", None)]

            if total_pages > 1:
                options.append(f"< Prev page ({page_index + 1}/{total_pages}) >")
                option_kinds.append(("prev", None))
                options.append(f"< Next page ({page_index + 1}/{total_pages}) >")
                option_kinds.append(("next", None))

            for idx, lic in enumerate(page_licenses):
                name = str(lic.get("spdx_license_key") or lic.get("license_key", ""))
                options.append(name)
                option_kinds.append(("license", start + idx))

            print(
                f"Page {page_index + 1}/{total_pages}. "
                "Use Up/Down to move. Prev/Next page controls are at the top. "
                "Enter to select, Esc to go back, Ctrl+C to cancel."
            )
            selected_index = _run_with_beaupy_interrupts(lambda: _beaupy_api().select(options, return_index=True))

            if selected_index is None:
                return None

            kind, payload = option_kinds[int(selected_index)]
            if kind == "back":
                return None
            if kind == "prev":
                page_index = (page_index - 1) % total_pages
                continue
            if kind == "next":
                page_index = (page_index + 1) % total_pages
                continue
            if payload is not None:
                return licenses[payload]

    for i, lic in enumerate(licenses, 1):
        name = lic.get("spdx_license_key") or lic.get("license_key", "")
        print(f"{i}. {name}")
    print("0. Back to filter")

    selection_str = input("Enter number: ").strip()
    try:
        selection = int(selection_str)
    except ValueError as exc:
        raise SystemExit("error: invalid selection.") from exc

    if selection == 0:
        return None
    if selection < 1 or selection > len(licenses):
        raise SystemExit("error: selection out of range.")

    return licenses[selection - 1]


def pick_license(
    project_dir: Path,
    python_version: str,
    scancode_index_url: str,
    scancode_base_url: str,
    urlopen: Callable[..., Any],
    update_pyproject_license_fn: Callable[[Path, str, str], None],
) -> None:
    """Interactively fetch, filter, and download a license from scancode-licensedb."""
    print("Fetching license index from scancode-licensedb...")
    try:
        with urlopen(scancode_index_url, timeout=30) as resp:  # noqa: S310
            all_licenses: list[dict[str, object]] = json.loads(resp.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: could not fetch license index: {exc}") from exc

    licenses = [
        lic
        for lic in all_licenses
        if not lic.get("is_exception") and not lic.get("is_deprecated") and lic.get("license")
    ]
    licenses.sort(
        key=lambda x: (
            str(x.get("spdx_license_key", "")),
            str(x.get("license_key", "")),
        )
    )

    if not licenses:
        raise SystemExit("error: no licenses found in remote index.")

    print(f"Found {len(licenses)} licenses.")

    try:
        while True:
            query = _prompt_text("Filter licenses by text (blank for all): ")
            if query:
                filtered = [
                    lic
                    for lic in licenses
                    if query.lower() in str(lic.get("spdx_license_key", "")).lower()
                    or query.lower() in str(lic.get("license_key", "")).lower()
                ]
                if not filtered:
                    raise SystemExit(f"error: no licenses matched filter: {query}")
                visible = filtered
            else:
                visible = licenses

            chosen = _select_license_with_back(visible)
            if chosen is not None:
                break
    except KeyboardInterrupt as exc:
        raise SystemExit("error: selection canceled by user") from exc

    file_name = str(chosen["license"])
    base_url = scancode_base_url.rstrip("/") + "/"
    url = base_url + file_name.lstrip("/")
    spdx_name = str(chosen.get("spdx_license_key") or chosen.get("license_key", file_name))

    print(f"Downloading {spdx_name}...")
    try:
        with urlopen(url, timeout=30) as resp:  # noqa: S310
            license_text = resp.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"error: could not download license: {exc}") from exc

    (project_dir / "LICENSE").write_text(license_text, encoding="utf-8")
    print(f"Downloaded {spdx_name} to {project_dir / 'LICENSE'}")
    update_pyproject_license_fn(project_dir, spdx_name, python_version)
