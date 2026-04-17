# pyright: reportPrivateLocalImportUsage=false,reportPrivateUsage=false,reportUnknownLambdaType=false,reportUnusedParameter=false,reportUnannotatedClassAttribute=false

import tomllib
from pathlib import Path

import pytest

from pyptmpl.creator_core import license_ops
from pyptmpl.tests._helpers import FakeResponse


@pytest.mark.parametrize(
    ("spdx", "classifiers", "expected"),
    [
        (
            "LGPL-3.0-or-later",
            ["License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)"],
            "LGPLv3+",
        ),
        (
            "MIT",
            [
                "License :: OSI Approved :: MIT No Attribution License (MIT-0)",
                "License :: OSI Approved :: MIT License",
            ],
            "MIT License",
        ),
        ("Unlicense", ["License :: Public Domain"], "Public Domain"),
    ],
)
def test_match_pypi_classifier(spdx: str, classifiers: list[str], expected: str) -> None:
    got = license_ops.match_pypi_classifier(spdx, classifiers)
    assert expected in got


def test_match_pypi_classifier_extra_branches() -> None:
    assert license_ops.match_pypi_classifier("???", ["License :: X"]) == "License :: Other/Proprietary License"
    assert (
        license_ops.match_pypi_classifier("Unlicense", ["License :: Weird"]) == "License :: Other/Proprietary License"
    )
    got = license_ops.match_pypi_classifier("BSD", ["License :: FooBSDLike"])
    assert got == "License :: FooBSDLike"
    got2 = license_ops.match_pypi_classifier("MIT-or-later", ["License :: MIT-style"])
    assert "MIT-style" in got2
    got3 = license_ops.match_pypi_classifier("0BSD", ["License :: OSI Approved :: BSD License"])
    assert "BSD" in got3


def test_match_pypi_classifier_continue_then_none() -> None:
    classifiers = [
        "License :: OSI Approved :: MIT License",
        "License :: Other/Proprietary License",
    ]
    assert license_ops.match_pypi_classifier("BSD-3-Clause", classifiers) == "License :: Other/Proprietary License"


def test_update_pyproject_license_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    license_ops.update_pyproject_license(tmp_path, "MIT", "3.13", lambda _: "License :: X")
    out = capsys.readouterr().out
    assert "skipping pyproject" in out


def test_update_pyproject_license_existing_block(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nreadme = "README.md"\nlicense = "Old"\nrequires-python = ">=3.13"\nclassifiers = [\n  "Old"\n]\n',
        encoding="utf-8",
    )

    license_ops.update_pyproject_license(
        tmp_path,
        "MIT",
        "3.13",
        lambda _: "License :: OSI Approved :: MIT License",
    )
    text = pyproject.read_text(encoding="utf-8")
    assert 'license = "MIT"' in text
    assert "MIT License" in text


def test_update_pyproject_license_insert_paths(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nreadme = "README.md"\nrequires-python = ">=3.13"\n',
        encoding="utf-8",
    )
    license_ops.update_pyproject_license(
        tmp_path,
        "Custom",
        "3.13",
        lambda _: "License :: Other/Proprietary License",
    )
    text = pyproject.read_text(encoding="utf-8")
    assert 'license = "Custom"' in text
    assert "classifiers = [" in text

    pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")
    license_ops.update_pyproject_license(
        tmp_path,
        "Custom2",
        "3.13",
        lambda _: "License :: Other/Proprietary License",
    )
    text2 = pyproject.read_text(encoding="utf-8")
    assert 'license = "Custom2"' in text2
    assert "classifiers = [" in text2


def test_update_pyproject_license_missing_project_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.x]\na = 1\n", encoding="utf-8")
    license_ops.update_pyproject_license(tmp_path, "MIT", "3.13", lambda _: "License :: X")
    out = capsys.readouterr().out
    assert "[project] table not found" in out


def test_update_pyproject_license_inline_project_table_without_header(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('project = { name = "x" }\n', encoding="utf-8")
    license_ops.update_pyproject_license(
        tmp_path,
        "MIT",
        "3.13",
        lambda _: "License :: OSI Approved :: MIT License",
    )
    out = capsys.readouterr().out
    assert "[project] table not found" in out


def test_update_pyproject_license_invalid_toml(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project\n", encoding="utf-8")
    license_ops.update_pyproject_license(tmp_path, "MIT", "3.13", lambda _: "License :: X")
    out = capsys.readouterr().out
    assert "invalid pyproject.toml" in out


def test_update_pyproject_license_preserves_following_table(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\nrequires-python = ">=3.13"\n[tool.ruff]\nline-length = 120\n',
        encoding="utf-8",
    )
    license_ops.update_pyproject_license(
        tmp_path,
        "MIT",
        "3.13",
        lambda _: "License :: OSI Approved :: MIT License",
    )
    text = pyproject.read_text(encoding="utf-8")
    assert "[tool.ruff]" in text
    assert "line-length = 120" in text


def test_pick_license_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index_json = """[
      {"license":"mit.LICENSE","spdx_license_key":"MIT","license_key":"mit","is_exception":false,"is_deprecated":false},
      {"license":"lgpl.LICENSE","spdx_license_key":"LGPL-3.0-or-later","license_key":"lgpl","is_exception":false,"is_deprecated":false}
    ]"""

    def fake_urlopen(url: str, timeout: int = 30) -> FakeResponse:
        if url == "INDEX":
            return FakeResponse(index_json)
        assert url.endswith("mit.LICENSE")
        return FakeResponse("MIT text")

    responses = iter(["MIT", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    captured: dict[str, str] = {}

    def fake_update(project_dir: Path, spdx_name: str, python_version: str) -> None:
        captured["spdx"] = spdx_name
        captured["py"] = python_version

    license_ops.pick_license(
        tmp_path,
        "3.13",
        "INDEX",
        "BASE/",
        fake_urlopen,
        fake_update,
    )

    assert (tmp_path / "LICENSE").read_text(encoding="utf-8") == "MIT text"
    assert captured == {"spdx": "MIT", "py": "3.13"}


def test_pick_license_base_url_without_trailing_slash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index_json = """[
      {"license":"mit.LICENSE","spdx_license_key":"MIT","license_key":"mit","is_exception":false,"is_deprecated":false}
    ]"""

    seen_urls: list[str] = []

    def fake_urlopen(url: str, timeout: int = 30) -> FakeResponse:
        del timeout
        seen_urls.append(url)
        if url == "INDEX":
            return FakeResponse(index_json)
        assert url == "BASE/mit.LICENSE"
        return FakeResponse("MIT text")

    answers = iter(["", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    license_ops.pick_license(
        tmp_path,
        "3.13",
        "INDEX",
        "BASE",
        fake_urlopen,
        lambda *_: None,
    )

    assert seen_urls == ["INDEX", "BASE/mit.LICENSE"]


def test_pick_license_errors(tmp_path: Path) -> None:
    def fail_urlopen(url: str, timeout: int = 30) -> FakeResponse:
        raise OSError("net down")

    with pytest.raises(SystemExit):
        license_ops.pick_license(
            tmp_path,
            "3.13",
            "INDEX",
            "BASE/",
            fail_urlopen,
            lambda *_: None,
        )


def test_pick_license_validation_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "")
    with pytest.raises(SystemExit):
        license_ops.pick_license(
            tmp_path,
            "3.13",
            "INDEX",
            "BASE/",
            lambda *_args, **_kwargs: FakeResponse("[]"),
            lambda *_: None,
        )

    one = '[{"license":"mit.LICENSE","spdx_license_key":"MIT","license_key":"mit","is_exception":false,"is_deprecated":false}]'

    def open_one(url: str, timeout: int = 30) -> FakeResponse:
        del timeout
        if url == "INDEX":
            return FakeResponse(one)
        return FakeResponse("MIT text")

    monkeypatch.setattr("builtins.input", lambda _: "zzz")
    with pytest.raises(SystemExit):
        license_ops.pick_license(tmp_path, "3.13", "INDEX", "BASE/", open_one, lambda *_: None)

    answers = iter(["", "abc"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    with pytest.raises(SystemExit):
        license_ops.pick_license(tmp_path, "3.13", "INDEX", "BASE/", open_one, lambda *_: None)

    answers2 = iter(["", "9"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers2))
    with pytest.raises(SystemExit):
        license_ops.pick_license(tmp_path, "3.13", "INDEX", "BASE/", open_one, lambda *_: None)

    answers3 = iter(["", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers3))

    def open_fail_download(url: str, timeout: int = 30) -> FakeResponse:
        del timeout
        if url == "INDEX":
            return FakeResponse(one)
        raise OSError("download failed")

    with pytest.raises(SystemExit):
        license_ops.pick_license(
            tmp_path,
            "3.13",
            "INDEX",
            "BASE/",
            open_fail_download,
            lambda *_: None,
        )


def test_pick_license_back_to_filter_in_text_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index_json = """[
      {"license":"mit.LICENSE","spdx_license_key":"MIT","license_key":"mit","is_exception":false,"is_deprecated":false},
      {"license":"lgpl.LICENSE","spdx_license_key":"LGPL-3.0-or-later","license_key":"lgpl","is_exception":false,"is_deprecated":false}
    ]"""

    seen_urls: list[str] = []

    def fake_urlopen(url: str, timeout: int = 30) -> FakeResponse:
        del timeout
        seen_urls.append(url)
        if url == "INDEX":
            return FakeResponse(index_json)
        return FakeResponse("MIT text")

    answers = iter(["", "0", "MIT", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    captured: dict[str, str] = {}
    license_ops.pick_license(
        tmp_path,
        "3.13",
        "INDEX",
        "BASE/",
        fake_urlopen,
        lambda _project_dir, spdx_name, _py: captured.update({"spdx": spdx_name}),
    )

    assert captured["spdx"] == "MIT"
    assert seen_urls == ["INDEX", "BASE/mit.LICENSE"]


def test_select_license_with_back_uses_beaupy_when_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(license_ops, "_can_use_beaupy", lambda: True)

    class _FakeBeaupy:
        @staticmethod
        def select(options, return_index=False, pagination=False, page_size=5):  # noqa: ANN001
            assert return_index is True
            assert pagination is True
            assert page_size == 12
            assert options[0] == "< Back to filter >"
            return 1

    monkeypatch.setattr(license_ops, "beaupy", _FakeBeaupy())
    got = license_ops._select_license_with_back(
        [
            {"spdx_license_key": "MIT", "license": "mit.LICENSE"},
            {"spdx_license_key": "BSD-3-Clause", "license": "bsd.LICENSE"},
        ]
    )
    assert got is not None
    assert got["spdx_license_key"] == "MIT"


def test_select_license_with_back_beaupy_back_and_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(license_ops, "_can_use_beaupy", lambda: True)

    class _BackBeaupy:
        @staticmethod
        def select(options, return_index=False, pagination=False, page_size=5):  # noqa: ANN001
            del options, return_index, pagination, page_size
            return 0

    monkeypatch.setattr(license_ops, "beaupy", _BackBeaupy())
    assert license_ops._select_license_with_back([{"spdx_license_key": "MIT", "license": "mit.LICENSE"}]) is None

    class _CancelBeaupy:
        @staticmethod
        def select(options, return_index=False, pagination=False, page_size=5):  # noqa: ANN001
            del options, return_index, pagination, page_size
            return None

    monkeypatch.setattr(license_ops, "beaupy", _CancelBeaupy())
    assert license_ops._select_license_with_back([{"spdx_license_key": "MIT", "license": "mit.LICENSE"}]) is None


def test_prompt_text_uses_beaupy_when_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(license_ops, "_can_use_beaupy", lambda: True)

    class _FakeBeaupy:
        @staticmethod
        def prompt(prompt: str):
            assert "Filter" in prompt
            return "  MIT  "

    monkeypatch.setattr(license_ops, "beaupy", _FakeBeaupy())
    assert license_ops._prompt_text("Filter licenses by text (blank for all): ") == "MIT"


def test_prompt_text_beaupy_none_value_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(license_ops, "_can_use_beaupy", lambda: True)

    class _FakeBeaupy:
        @staticmethod
        def prompt(prompt: str):
            del prompt
            return None

    monkeypatch.setattr(license_ops, "beaupy", _FakeBeaupy())
    assert license_ops._prompt_text("Filter licenses by text (blank for all): ") == ""


def test_replace_project_scalar_updates_existing_key() -> None:
    section = ['name = "x"', 'license = "Old"', 'requires-python = ">=3.13"']
    updated = license_ops._replace_project_scalar(section[:], "license", "MIT")
    assert updated[1] == 'license = "MIT"'
    assert updated.count('license = "MIT"') == 1


def test_replace_project_classifiers_replaces_block_and_inserts_after_requires_python() -> None:
    section = [
        'name = "x"',
        'requires-python = ">=3.13"',
        "classifiers = [",
        '  "Old",',
        "]",
        "dependencies = []",
    ]
    updated = license_ops._replace_project_classifiers(section, ["License :: X", "Programming Language :: Python :: 3"])
    requires_idx = updated.index('requires-python = ">=3.13"')
    assert updated[requires_idx + 1] == "classifiers = ["
    assert '  "License :: X",' in updated
    assert "dependencies = []" in updated
    assert '  "Old",' not in updated


def test_replace_project_classifiers_handles_unclosed_existing_block() -> None:
    section = [
        'name = "x"',
        "classifiers = [",
        '  "Old",',
    ]
    updated = license_ops._replace_project_classifiers(section, ["License :: X"])
    assert updated == ['name = "x"', "classifiers = [", '  "License :: X",', "]"]


def test_match_pypi_classifier_prefers_later_match_when_earlier_is_non_match() -> None:
    classifiers = [
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    ]
    got = license_ops.match_pypi_classifier("LGPL-3.0-or-later", classifiers)
    assert "LGPLv3+" in got


def test_match_pypi_classifier_or_later_penalty_and_bonus() -> None:
    classifiers = [
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ]
    got = license_ops.match_pypi_classifier("GPL-3.0-or-later", classifiers)
    assert "or later" in got.lower()


def test_pick_license_prints_selection_from_license_key_when_spdx_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    index_json = """[
      {"license":"a.LICENSE","license_key":"aaa","is_exception":false,"is_deprecated":false}
    ]"""

    def fake_urlopen(url: str, timeout: int = 30) -> FakeResponse:
        del timeout
        if url == "INDEX":
            return FakeResponse(index_json)
        return FakeResponse("license text")

    answers = iter(["", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    license_ops.pick_license(tmp_path, "3.13", "INDEX", "BASE/", fake_urlopen, lambda *_: None)
    out = capsys.readouterr().out
    assert "1. aaa" in out


def test_match_pypi_classifier_numeric_base_does_not_match_empty_candidate() -> None:
    classifiers = ["License :: OSI Approved :: MIT License"]
    got = license_ops.match_pypi_classifier("123-foo", classifiers)
    assert got == "License :: Other/Proprietary License"


def test_match_pypi_classifier_prefers_matching_version_when_available() -> None:
    classifiers = [
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ]
    got = license_ops.match_pypi_classifier("GPL-3.0-only", classifiers)
    assert "v3" in got.lower()


def test_match_pypi_classifier_prefers_non_or_later_for_non_or_later_spdx() -> None:
    classifiers = [
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ]
    got = license_ops.match_pypi_classifier("GPL-3.0-only", classifiers)
    assert "or later" not in got.lower()


def test_replace_project_classifiers_preserves_lines_after_closed_block() -> None:
    section = [
        'name = "x"',
        "classifiers = [",
        '  "Old",',
        "]",
        'description = "kept"',
    ]
    updated = license_ops._replace_project_classifiers(section, ["License :: X"])
    assert 'description = "kept"' in updated
    assert updated[-1] == "]"


def test_replace_project_classifiers_exact_structure_after_replacement() -> None:
    section = [
        'name = "x"',
        "classifiers = [",
        '  "Old",',
        "]",
        'description = "kept"',
    ]
    updated = license_ops._replace_project_classifiers(section, ["License :: X", "License :: Y"])
    assert updated == [
        'name = "x"',
        'description = "kept"',
        "classifiers = [",
        '  "License :: X",',
        '  "License :: Y",',
        "]",
    ]


def test_replace_project_classifiers_inserts_after_first_requires_python() -> None:
    section = [
        'name = "x"',
        'requires-python = ">=3.13"',
        'requires-python = ">=3.14"',
        'description = "x"',
    ]
    updated = license_ops._replace_project_classifiers(section, ["License :: X"])
    first_requires = updated.index('requires-python = ">=3.13"')
    assert updated[first_requires + 1] == "classifiers = ["


def test_update_pyproject_license_keeps_tool_section_unmodified(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "x"
requires-python = ">=3.13"

[tool.custom]
license = "TOOL"
""",
        encoding="utf-8",
    )
    license_ops.update_pyproject_license(
        tmp_path,
        "MIT",
        "3.13",
        lambda _: "License :: OSI Approved :: MIT License",
    )
    text = pyproject.read_text(encoding="utf-8")
    assert '[tool.custom]\nlicense = "TOOL"' in text
    assert 'license = "MIT"' in text


def test_update_pyproject_license_stops_at_first_following_table(
    tmp_path: Path,
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "x"
requires-python = ">=3.13"

[tool.first]
setting = 1

[tool.last]
setting = 2
""",
        encoding="utf-8",
    )
    license_ops.update_pyproject_license(
        tmp_path,
        "MIT",
        "3.13",
        lambda _: "License :: OSI Approved :: MIT License",
    )
    text = pyproject.read_text(encoding="utf-8")
    assert "[tool.first]\nsetting = 1" in text
    assert "[tool.last]\nsetting = 2" in text
    assert text.count("[tool.first]") == 1
    assert text.count("[tool.last]") == 1


def test_match_pypi_classifier_negative_one_score_still_falls_back() -> None:
    # This case produces score -1 for the only candidate; fallback should remain Other/Proprietary.
    got = license_ops.match_pypi_classifier(
        "ABC-or-later",
        ["License :: XABCY"],
    )
    assert got == "License :: Other/Proprietary License"


def test_match_pypi_classifier_non_digit_abbrev_not_penalized_as_if_numeric() -> None:
    classifiers = [
        "License :: OSI Approved :: MIT-style (MITX)",
        "License :: MIT",
    ]
    got = license_ops.match_pypi_classifier("MIT", classifiers)
    assert "MITX" in got


def test_update_pyproject_license_does_not_treat_array_closing_bracket_as_table_header(
    tmp_path: Path,
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "x"
requires-python = ">=3.13"
classifiers = [
  "Old",
]
dependencies = ["a"]

[tool.keep]
value = 1
""",
        encoding="utf-8",
    )

    license_ops.update_pyproject_license(
        tmp_path,
        "MIT",
        "3.13",
        lambda _: "License :: OSI Approved :: MIT License",
    )

    text = pyproject.read_text(encoding="utf-8")
    assert 'dependencies = ["a"]' in text
    assert "[tool.keep]\nvalue = 1" in text


def test_update_pyproject_license_replaces_existing_classifiers_with_single_well_formed_block(
    tmp_path: Path,
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "x"
requires-python = ">=3.13"
classifiers = [
  "Old A",
  "Old B",
]
dependencies = ["dep"]

[tool.keep]
x = 1
""",
        encoding="utf-8",
    )

    license_ops.update_pyproject_license(
        tmp_path,
        "MIT",
        "3.13",
        lambda _: "License :: OSI Approved :: MIT License",
    )

    text = pyproject.read_text(encoding="utf-8")
    assert text.count("classifiers = [") == 1
    assert "Old A" not in text
    assert "Old B" not in text
    assert 'dependencies = ["dep"]' in text
    assert "[tool.keep]\nx = 1" in text

    # Output must remain valid TOML and keep [project]/[tool.keep] boundaries.
    parsed = tomllib.loads(text)
    assert parsed["project"]["license"] == "MIT"
    assert parsed["tool"]["keep"]["x"] == 1
