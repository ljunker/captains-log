from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine
from sqlalchemy.engine import Connection


BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "app" / "migrations"
VERSION_TABLE_NAME = "schema_version"
INITIAL_SCHEMA_VERSION = 0
MIGRATION_FILENAME_RE = re.compile(r"^(?P<version>\d{3})_[a-z0-9_]+\.sql$")


@dataclass(frozen=True)
class Migration:
    version: int
    path: Path


def run_migrations(engine: Engine) -> None:
    migrations = _load_migrations()

    with engine.begin() as connection:
        _ensure_version_table(connection)
        current_version = _get_current_version(connection)

        initial_migration = next((migration for migration in migrations if migration.version == INITIAL_SCHEMA_VERSION), None)
        if current_version == INITIAL_SCHEMA_VERSION and initial_migration and _database_needs_bootstrap(connection):
            _apply_sql_script(connection, initial_migration.path)

        for migration in migrations:
            if migration.version <= current_version:
                continue

            _apply_sql_script(connection, migration.path)
            connection.exec_driver_sql(
                f"UPDATE {VERSION_TABLE_NAME} SET version = ? WHERE id = 1",
                (migration.version,),
            )


def _load_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    seen_versions: set[int] = set()

    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = MIGRATION_FILENAME_RE.match(path.name)
        if match is None:
            raise RuntimeError(f"Invalid migration filename: {path.name}")

        version = int(match.group("version"))
        if version in seen_versions:
            raise RuntimeError(f"Duplicate migration version: {version:03d}")

        seen_versions.add(version)
        migrations.append(Migration(version=version, path=path))

    if not migrations:
        raise RuntimeError(f"No migration files found in {MIGRATIONS_DIR}")

    if migrations[0].version != INITIAL_SCHEMA_VERSION:
        raise RuntimeError("The first migration must be 000_initial.sql")

    return migrations


def _ensure_version_table(connection: Connection) -> None:
    connection.exec_driver_sql(
        f"""
        CREATE TABLE IF NOT EXISTS {VERSION_TABLE_NAME} (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        f"""
        INSERT INTO {VERSION_TABLE_NAME} (id, version)
        SELECT 1, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM {VERSION_TABLE_NAME} WHERE id = 1
        )
        """,
        (INITIAL_SCHEMA_VERSION,),
    )


def _get_current_version(connection: Connection) -> int:
    version = connection.exec_driver_sql(
        f"SELECT version FROM {VERSION_TABLE_NAME} WHERE id = 1"
    ).scalar_one_or_none()

    if version is None:
        raise RuntimeError(f"{VERSION_TABLE_NAME} is missing the row with id=1")

    return int(version)


def _database_needs_bootstrap(connection: Connection) -> bool:
    table_names = connection.exec_driver_sql(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).scalars()

    application_tables = {name for name in table_names if name != VERSION_TABLE_NAME}
    return not application_tables


def _apply_sql_script(connection: Connection, path: Path) -> None:
    script = path.read_text(encoding="utf-8")
    for statement in _iter_sql_statements(script):
        connection.exec_driver_sql(statement)


def _iter_sql_statements(script: str) -> Iterator[str]:
    chunk: list[str] = []

    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        chunk.append(line)
        statement = "\n".join(chunk)

        if sqlite3.complete_statement(statement):
            prepared = statement.strip()
            if prepared.endswith(";"):
                prepared = prepared[:-1]
            if prepared:
                yield prepared
            chunk = []

    if chunk:
        raise RuntimeError("Migration script ended with an incomplete SQL statement")
