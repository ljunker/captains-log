from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "dockerhub-up"
LOADER = importlib.machinery.SourceFileLoader("dockerhub_up", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader("dockerhub_up", LOADER)
assert SPEC is not None
assert SPEC.loader is not None
dockerhub_up = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dockerhub_up)


def test_resolve_requested_version_prefers_argument_over_env_and_file(tmp_path: Path, monkeypatch) -> None:
    version_file = tmp_path / "version.txt"
    version_file.write_text("2.0.0\n", encoding="utf-8")
    monkeypatch.setenv("DOCKER_IMAGE_VERSION", "1.5.0")

    version, source = dockerhub_up.resolve_requested_version("3.1.4", version_file)

    assert version == "3.1.4"
    assert source == "argument"


def test_resolve_requested_version_uses_file_before_default(tmp_path: Path, monkeypatch) -> None:
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.7.0\n", encoding="utf-8")
    monkeypatch.delenv("DOCKER_IMAGE_VERSION", raising=False)

    version, source = dockerhub_up.resolve_requested_version(None, version_file)

    assert version == "1.7.0"
    assert source == "file:version.txt"


def test_fetch_latest_dockerhub_version_prefers_highest_semver(monkeypatch) -> None:
    def fake_fetch_json(url: str, timeout: float = 5.0) -> dict:
        assert "tags?page_size=100" in url
        return {
            "results": [
                {"name": "latest"},
                {"name": "1"},
                {"name": "1.2"},
                {"name": "1.4.3"},
                {"name": "1.10.0"},
                {"name": "0.9.1"},
            ]
        }

    monkeypatch.setattr(dockerhub_up, "fetch_json", fake_fetch_json)

    version = dockerhub_up.fetch_latest_dockerhub_version("kryptikker/captains-log")

    assert version == "1.10.0"


def test_fetch_latest_dockerhub_version_falls_back_to_latest_tag(monkeypatch) -> None:
    calls: list[str] = []

    def fake_fetch_json(url: str, timeout: float = 5.0) -> dict:
        calls.append(url)
        if "tags?page_size=100" in url:
            return {"results": [{"name": "latest"}, {"name": "1"}, {"name": "1.2"}]}
        return {"name": "latest"}

    monkeypatch.setattr(dockerhub_up, "fetch_json", fake_fetch_json)

    version = dockerhub_up.fetch_latest_dockerhub_version("kryptikker/captains-log")

    assert version == "latest"
    assert any("tags/latest" in call for call in calls)


def test_deploy_exports_repository_and_version(monkeypatch) -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(command: list[str], check: bool, env: dict[str, str]) -> None:
        assert check is True
        calls.append((command, env))

    monkeypatch.setattr(dockerhub_up.subprocess, "run", fake_run)

    dockerhub_up.deploy("kryptikker/captains-log", "1.2.0", dry_run=False)

    assert calls[0][0] == ["docker", "compose", "pull", "app"]
    assert calls[1][0] == ["docker", "compose", "up", "-d", "app"]
    assert calls[0][1]["DOCKER_IMAGE_REPOSITORY"] == "kryptikker/captains-log"
    assert calls[0][1]["DOCKER_IMAGE_VERSION"] == "1.2.0"


def test_main_skips_deploy_when_container_already_uses_requested_image(monkeypatch) -> None:
    deploy_calls: list[tuple[str, str, bool]] = []

    monkeypatch.setattr(dockerhub_up, "fetch_latest_dockerhub_version", lambda repository: "1.2.0")
    monkeypatch.setattr(dockerhub_up, "get_running_image_ref", lambda: "kryptikker/captains-log:1.2.0")
    monkeypatch.setattr(
        dockerhub_up,
        "deploy",
        lambda repository, version, dry_run: deploy_calls.append((repository, version, dry_run)),
    )

    exit_code = dockerhub_up.main(["--version", "1.2.0"])

    assert exit_code == 0
    assert deploy_calls == []


def test_main_deploys_when_container_uses_different_image(monkeypatch) -> None:
    deploy_calls: list[tuple[str, str, bool]] = []

    monkeypatch.setattr(dockerhub_up, "fetch_latest_dockerhub_version", lambda repository: "1.2.0")
    monkeypatch.setattr(dockerhub_up, "get_running_image_ref", lambda: "kryptikker/captains-log:1.1.0")
    monkeypatch.setattr(
        dockerhub_up,
        "deploy",
        lambda repository, version, dry_run: deploy_calls.append((repository, version, dry_run)),
    )

    exit_code = dockerhub_up.main(["--version", "1.2.0"])

    assert exit_code == 0
    assert deploy_calls == [("kryptikker/captains-log", "1.2.0", False)]
