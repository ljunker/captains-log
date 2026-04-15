from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import sqlite3
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "db-backup"
LOADER = importlib.machinery.SourceFileLoader("db_backup", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader("db_backup", LOADER)
assert SPEC is not None
assert SPEC.loader is not None
db_backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(db_backup)


def create_sqlite_database(path: Path, schema_version: int = 1) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            f"""
            CREATE TABLE schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            );
            INSERT INTO schema_version (id, version) VALUES (1, {schema_version});
            CREATE TABLE entries (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL
            );
            INSERT INTO entries (content) VALUES ('Backup Test');
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_create_and_verify_encrypted_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if shutil.which("openssl") is None:
        pytest.skip("openssl is required for encrypted backup tests")

    sqlite_path = tmp_path / "captains_log.db"
    backup_dir = tmp_path / "backups"
    create_sqlite_database(sqlite_path, schema_version=7)
    monkeypatch.setenv("BACKUP_PASSPHRASE", "super-secret-passphrase")

    backup_file = db_backup.create_backup(
        source_database=sqlite_path,
        backup_dir=backup_dir,
        prefix="captains-log-db",
        retention_days=30,
        passphrase="super-secret-passphrase",
    )

    assert backup_file.exists()
    assert backup_file.suffix == ".enc"

    status, version = db_backup.verify_backup(backup_file, "super-secret-passphrase")

    assert status == "ok"
    assert version == 7


def test_prune_old_backups_deletes_files_older_than_retention(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    old_backup = backup_dir / "captains-log-db-old.sqlite3.gz.enc"
    new_backup = backup_dir / "captains-log-db-new.sqlite3.gz.enc"
    old_backup.write_bytes(b"old")
    new_backup.write_bytes(b"new")

    old_timestamp = (datetime.now(UTC) - timedelta(days=31)).timestamp()
    new_timestamp = (datetime.now(UTC) - timedelta(days=5)).timestamp()
    os.utime(old_backup, (old_timestamp, old_timestamp))
    os.utime(new_backup, (new_timestamp, new_timestamp))

    deleted = db_backup.prune_old_backups(backup_dir, retention_days=30)

    assert deleted == [old_backup]
    assert not old_backup.exists()
    assert new_backup.exists()


def test_resolve_source_database_prefers_database_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sqlite_path = tmp_path / "captains_log.db"
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{sqlite_path}")

    resolved = db_backup.resolve_source_database(None, None, "captains_log.db")

    assert resolved == sqlite_path.resolve()


def test_resolve_source_database_uses_docker_volume(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    volume_mount = tmp_path / "volume"
    volume_mount.mkdir()
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db_backup, "inspect_docker_volume_mountpoint", lambda volume_name: volume_mount)

    resolved = db_backup.resolve_source_database(None, "captains_log_data", "captains_log.db")

    assert resolved == (volume_mount / "captains_log.db").resolve()


def test_script_is_executable() -> None:
    mode = SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR
