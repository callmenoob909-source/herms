"""Regression coverage for desktop userData policy during agent uninstall."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import hermes_cli.uninstall as uninstall


@pytest.fixture
def uninstall_env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    project_root = tmp_path / "checkout"
    home.mkdir()
    project_root.mkdir()
    (home / "config.yaml").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(uninstall, "_is_windows", lambda: False)
    monkeypatch.setattr(uninstall, "uninstall_gateway_service", lambda: True)
    monkeypatch.setattr(uninstall, "remove_path_from_shell_configs", lambda: [])
    monkeypatch.setattr(uninstall, "remove_wrapper_script", lambda: [])
    monkeypatch.setattr(uninstall, "remove_node_symlinks", lambda *_: [])
    monkeypatch.setattr(uninstall, "remove_legacy_runtime_trees", lambda *_: [])
    return home, project_root


@pytest.mark.parametrize(
    ("full_uninstall", "expected_remove_userdata"),
    [(False, False), (True, True)],
)
def test_agent_uninstall_forwards_desktop_userdata_policy(
    uninstall_env, monkeypatch, full_uninstall, expected_remove_userdata
):
    home, project_root = uninstall_env
    calls = []

    def fake_uninstall_gui(_home, *, remove_userdata=True):
        calls.append(remove_userdata)
        return [Path("desktop-artifact")]

    monkeypatch.setattr("hermes_cli.gui_uninstall.uninstall_gui", fake_uninstall_gui)

    uninstall._perform_uninstall(
        project_root=project_root,
        hermes_home=home,
        full_uninstall=full_uninstall,
        remove_profiles=False,
        named_profiles=[],
    )

    assert calls == [expected_remove_userdata]


def test_full_dry_run_lists_profiles_without_desktop_userdata(tmp_path, monkeypatch, capsys):
    missing_userdata = tmp_path / "missing-desktop-userdata"
    profile = SimpleNamespace(name="work", path=tmp_path / "profiles" / "work")

    monkeypatch.setattr("hermes_cli.gui_uninstall.desktop_userdata_dir", lambda: missing_userdata)
    monkeypatch.setattr(uninstall, "_is_default_hermes_home", lambda _home: True)
    monkeypatch.setattr(uninstall, "_discover_named_profiles", lambda: [profile])

    uninstall._print_uninstall_dry_run(
        project_root=tmp_path / "checkout",
        hermes_home=tmp_path / "home",
        full_uninstall=True,
    )

    output = capsys.readouterr().out
    assert "Named profiles" in output
    assert f"{profile.name}: {profile.path}" in output


def test_keep_data_dry_run_keeps_desktop_data_without_listing_profiles(
    tmp_path, monkeypatch, capsys
):
    userdata = tmp_path / "Hermes"
    userdata.mkdir()
    profile = SimpleNamespace(name="work", path=tmp_path / "profiles" / "work")

    monkeypatch.setattr("hermes_cli.gui_uninstall.desktop_userdata_dir", lambda: userdata)
    monkeypatch.setattr(uninstall, "_is_default_hermes_home", lambda _home: True)
    monkeypatch.setattr(uninstall, "_discover_named_profiles", lambda: [profile])

    uninstall._print_uninstall_dry_run(
        project_root=tmp_path / "checkout",
        hermes_home=tmp_path / "home",
        full_uninstall=False,
    )

    output = capsys.readouterr().out
    assert f"Keep desktop app data: {userdata}" in output
    assert "Named profiles" not in output
    assert str(profile.path) not in output
