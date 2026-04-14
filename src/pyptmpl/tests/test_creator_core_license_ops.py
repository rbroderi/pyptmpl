# pyright: reportPrivateLocalImportUsage=false,reportUnknownLambdaType=false,reportUnusedParameter=false,reportUnannotatedClassAttribute=false

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
