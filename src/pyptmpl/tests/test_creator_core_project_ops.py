# pyright: reportPrivateLocalImportUsage=false,reportUnknownLambdaType=false,reportUnusedParameter=false,reportUnannotatedClassAttribute=false

import subprocess
from pathlib import Path

import pytest

from pyptmpl.creator_core import project_ops
from pyptmpl.creator_core import templates
from pyptmpl.tests._helpers import CommandRecorder


def test_check_uv_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_ops.shutil, "which", lambda _: None)
    with pytest.raises(SystemExit):
        project_ops.check_uv()


def test_check_uv_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_ops.shutil, "which", lambda _: "uv")
    project_ops.check_uv()


def test_get_git_author_with_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_ops.shutil, "which", lambda _: "git")

    def fake_check_output(cmd: list[str], text: bool, stderr: int) -> str:
        if cmd[-1] == "user.name":
            return "Alice\n"
        return "alice@example.com\n"

    monkeypatch.setattr(project_ops.subprocess, "check_output", fake_check_output)
    got = project_ops.get_git_author()
    assert got.name == "Alice"
    assert got.email == "alice@example.com"


def test_get_git_author_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_ops.shutil, "which", lambda _: "git")

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(project_ops.subprocess, "check_output", fail)
    got = project_ops.get_git_author()
    assert got.name == "Your Name"
    assert got.email == "you@example.com"


def test_run_cmd_raises_on_non_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    class R:
        returncode = 3

    monkeypatch.setattr(project_ops.subprocess, "run", lambda cmd, cwd=None: R())
    with pytest.raises(SystemExit):
        project_ops.run_cmd(["x"])


def test_init_project_underscore_candidate(tmp_path: Path) -> None:
    called: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None) -> None:
        called.append(cmd)
        (tmp_path / "my_proj").mkdir()

    result = project_ops.init_project("my-proj", "3.13", tmp_path, fake_run)

    assert called[0][:4] == ["uv", "init", "--lib", "--python"]
    assert result == tmp_path / "my_proj"


def test_init_project_not_found(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        project_ops.init_project("missing", "3.13", tmp_path, lambda *_: None)


def test_write_pyproject(tmp_path: Path) -> None:
    project_ops.write_pyproject(
        tmp_path,
        project_name="proj",
        package_name="proj",
        python_version="3.13",
        description="desc",
        author=project_ops.GitAuthor("A", "a@b"),
        default_license_id="LGPL-3.0-or-later",
        load_template=lambda _: (
            "name={{project_name}}\nlicense={{license_id}}\ncls={{license_classifier}}"
        ),
        render_template=templates.render_template,
        get_license_classifier=lambda _: "License :: X",
    )

    text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert "name=proj" in text
    assert "license=LGPL-3.0-or-later" in text
    assert "cls=License :: X" in text


def test_create_smoke_test(tmp_path: Path) -> None:
    project_ops.create_smoke_test(
        tmp_path,
        "pkg",
        load_template=lambda _: "import {{package_name}}",
        render_template=templates.render_template,
    )
    smoke = tmp_path / "src" / "pkg" / "tests" / "test_smoke.py"
    assert smoke.exists()
    assert "import pkg" in smoke.read_text(encoding="utf-8")


def test_create_venv(tmp_path: Path) -> None:
    recorder = CommandRecorder()
    project_ops.create_venv(tmp_path, "3.13", recorder)
    assert recorder.calls == [["uv", "venv", "--python", "3.13"]]


def test_sync_project(tmp_path: Path) -> None:
    recorder = CommandRecorder()
    project_ops.sync_project(tmp_path, recorder)
    assert recorder.calls == [
        ["uv", "sync", "--extra", "dev", "--extra", "docs", "--extra", "build"]
    ]


def test_setup_gitignore_create_and_update(tmp_path: Path) -> None:
    project_ops.setup_gitignore(tmp_path, lambda _: "a\nb\n")
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "a\nb\n"

    (tmp_path / ".gitignore").write_text("a\n", encoding="utf-8")
    project_ops.setup_gitignore(tmp_path, lambda _: "a\nb\n")
    assert "b" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_setup_gitignore_already_has_defaults(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("a\nb\n", encoding="utf-8")
    project_ops.setup_gitignore(tmp_path, lambda _: "a\nb\n")
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "a\nb\n"


def test_setup_yamllint(tmp_path: Path) -> None:
    project_ops.setup_yamllint(tmp_path, lambda _: "extends: default\n")
    assert (tmp_path / ".yamllint").exists()


def test_setup_yamllint_existing(tmp_path: Path) -> None:
    y = tmp_path / ".yamllint"
    y.write_text("x\n", encoding="utf-8")
    project_ops.setup_yamllint(tmp_path, lambda _: "extends: default\n")
    assert y.read_text(encoding="utf-8") == "x\n"


def test_setup_vscode(tmp_path: Path) -> None:
    project_ops.setup_vscode(
        tmp_path,
        lambda _: '{"python.defaultInterpreterPath": ".venv"}',
    )
    assert (tmp_path / ".vscode" / "settings.json").exists()


def test_setup_typos(tmp_path: Path) -> None:
    project_ops.setup_typos(
        tmp_path, lambda _: '[default.extend-words]\ndatas = "datas"\n'
    )
    typos_config = tmp_path / "typos.toml"
    assert typos_config.exists()
    assert "datas" in typos_config.read_text(encoding="utf-8")


def test_setup_typos_existing(tmp_path: Path) -> None:
    t = tmp_path / "typos.toml"
    t.write_text("x\n", encoding="utf-8")
    project_ops.setup_typos(
        tmp_path, lambda _: '[default.extend-words]\ndatas = "datas"\n'
    )
    assert t.read_text(encoding="utf-8") == "x\n"


def test_setup_justfiles(tmp_path: Path) -> None:
    project_ops.setup_justfiles(tmp_path, lambda _: "content")
    assert (tmp_path / "justfile").exists()
    assert not (tmp_path / ".justfiles").exists()


def test_setup_docs_build_assets(tmp_path: Path) -> None:
    project_ops.setup_docs_build_assets(
        tmp_path,
        "pkg",
        load_template=lambda _: "x={{package_name}}",
        render_template=templates.render_template,
    )

    assert (tmp_path / "docs" / "index.md").exists()
    assert (tmp_path / "docs" / "python-api.md").read_text(encoding="utf-8") == "x=pkg"
    assert (tmp_path / "docs_sphinx" / "conf.py").read_text(encoding="utf-8") == "x=pkg"
    assert (tmp_path / "zensical.toml").exists()
    assert (tmp_path / "build.spec").read_text(encoding="utf-8") == "x=pkg"


def test_infer_python_version_from_pyproject_found(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        'requires-python = ">=3.12"\n', encoding="utf-8"
    )
    assert (
        project_ops.infer_python_version_from_pyproject(tmp_path, default="3.11")
        == "3.12"
    )


def test_infer_python_version_default_paths(tmp_path: Path) -> None:
    assert (
        project_ops.infer_python_version_from_pyproject(tmp_path, default="3.10")
        == "3.10"
    )
    (tmp_path / "pyproject.toml").write_text('name = "x"\n', encoding="utf-8")
    assert (
        project_ops.infer_python_version_from_pyproject(tmp_path, default="3.9")
        == "3.9"
    )


def test_infer_python_version_from_pyproject_strict_errors(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        project_ops.infer_python_version_from_pyproject(
            tmp_path, default="3.11", strict=True
        )

    (tmp_path / "pyproject.toml").write_text('name = "x"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        project_ops.infer_python_version_from_pyproject(
            tmp_path, default="3.11", strict=True
        )


def test_infer_project_and_package_name(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('name = "my-proj"\n', encoding="utf-8")
    assert project_ops.infer_project_name_from_pyproject(tmp_path) == "my-proj"
    assert project_ops.infer_package_name_from_pyproject(tmp_path) == "my_proj"


def test_infer_project_name_strict_errors(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        project_ops.infer_project_name_from_pyproject(tmp_path, strict=True)

    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        project_ops.infer_project_name_from_pyproject(tmp_path, strict=True)


def test_infer_project_name_missing_name_strict_false(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nversion='0.1.0'\n", encoding="utf-8"
    )
    assert project_ops.infer_project_name_from_pyproject(tmp_path, strict=False) is None


def test_infer_package_name_none_branch(tmp_path: Path) -> None:
    assert project_ops.infer_package_name_from_pyproject(tmp_path) is None


def test_infer_project_name_missing_file_strict_false(tmp_path: Path) -> None:
    assert project_ops.infer_project_name_from_pyproject(tmp_path, strict=False) is None
