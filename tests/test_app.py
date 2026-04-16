from __future__ import annotations

import importlib
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


def test_entry_crud_flow(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "test.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)
    os.environ["API_KEY"] = "test-key"
    os.environ["APP_TIMEZONE"] = "UTC"

    for module_name in ["app.config", "app.database", "app.migration", "app.models", "app.main"]:
        sys.modules.pop(module_name, None)

    app_module = importlib.import_module("app.main")
    database_module = importlib.import_module("app.database")
    models_module = importlib.import_module("app.models")

    with TestClient(app_module.app) as client:
        headers = {"X-API-Key": "test-key"}

        unauthorized_response = client.get("/api/entries")
        assert unauthorized_response.status_code == 401

        today = datetime.now(UTC).replace(microsecond=0)
        yesterday = today - timedelta(days=1)

        db = database_module.SessionLocal()
        older_entry = models_module.Entry(content="Gestern")
        older_entry.created_at = yesterday
        older_entry.updated_at = yesterday
        db.add(older_entry)
        db.commit()
        db.close()

        create_response = client.post(
            "/api/entries",
            json={"content": "Erster Eintrag", "tags": ["Arbeit", "Python", "arbeit"]},
            headers=headers,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        entry_id = created["id"]
        assert created["created_at"].endswith("+00:00")
        assert created["tags"] == ["arbeit", "python"]

        list_response = client.get("/api/entries", headers=headers)
        assert list_response.status_code == 200
        listed = list_response.json()
        assert listed["day"] == today.date().isoformat()
        assert listed["previous_day"] == yesterday.date().isoformat()
        assert listed["next_day"] is None
        assert listed["active_tag"] is None
        assert listed["available_tags"] == ["arbeit", "python"]
        assert len(listed["entries"]) == 1

        filtered_response = client.get("/api/entries?tag=python", headers=headers)
        assert filtered_response.status_code == 200
        filtered_payload = filtered_response.json()
        assert filtered_payload["active_tag"] == "python"
        assert filtered_payload["available_tags"] == ["arbeit", "python"]
        assert len(filtered_payload["entries"]) == 1
        assert filtered_payload["entries"][0]["tags"] == ["arbeit", "python"]

        tag_suggestions_response = client.get("/api/tags/suggestions?query=arb", headers=headers)
        assert tag_suggestions_response.status_code == 200
        assert tag_suggestions_response.json() == ["arbeit"]

        all_tag_suggestions_response = client.get("/api/tags/suggestions?query=", headers=headers)
        assert all_tag_suggestions_response.status_code == 200
        assert all_tag_suggestions_response.json() == ["arbeit", "python"]

        update_response = client.put(
            f"/api/entries/{entry_id}",
            json={"content": "Aktualisiert", "tags": ["Privat"]},
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["content"] == "Aktualisiert"
        assert update_response.json()["tags"] == ["privat"]

        missing_tag_response = client.get("/api/entries?tag=python", headers=headers)
        assert missing_tag_response.status_code == 200
        assert missing_tag_response.json()["entries"] == []

        previous_day_response = client.get(f"/api/entries?day={yesterday.date().isoformat()}", headers=headers)
        assert previous_day_response.status_code == 200
        previous_day_payload = previous_day_response.json()
        assert previous_day_payload["day"] == yesterday.date().isoformat()
        assert previous_day_payload["next_day"] == today.date().isoformat()
        assert previous_day_payload["available_tags"] == []
        assert len(previous_day_payload["entries"]) == 1

        delete_response = client.delete(f"/api/entries/{entry_id}", headers=headers)
        assert delete_response.status_code == 204

        missing_response = client.get(f"/api/entries/{entry_id}", headers=headers)
        assert missing_response.status_code == 404

    sqlite_connection = sqlite3.connect(sqlite_path)
    try:
        version = sqlite_connection.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        tags = sqlite_connection.execute("SELECT name FROM tags ORDER BY name").fetchall()
        assert version == (1,)
        assert tags == []
    finally:
        sqlite_connection.close()


def test_existing_unversioned_database_gets_version_table(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(sqlite_path)
    try:
        connection.executescript(
            """
            CREATE TABLE entries (
                id INTEGER NOT NULL,
                title VARCHAR(200) DEFAULT '' NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id)
            );
            CREATE INDEX ix_entries_id ON entries (id);
            INSERT INTO entries (content, created_at, updated_at)
            VALUES ('Altbestand', '2026-04-10 08:00:00', '2026-04-10 08:00:00');
            """
        )
        connection.commit()
    finally:
        connection.close()

    os.environ["SQLITE_PATH"] = str(sqlite_path)
    os.environ["API_KEY"] = "test-key"
    os.environ["APP_TIMEZONE"] = "UTC"

    for module_name in ["app.config", "app.database", "app.migration", "app.models", "app.main"]:
        sys.modules.pop(module_name, None)

    app_module = importlib.import_module("app.main")

    with TestClient(app_module.app) as client:
        response = client.get("/api/entries", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["entries"]) == 1
        assert payload["entries"][0]["content"] == "Altbestand"

    sqlite_connection = sqlite3.connect(sqlite_path)
    try:
        version = sqlite_connection.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        row_count = sqlite_connection.execute("SELECT COUNT(*) FROM entries").fetchone()
        tags_tables = sqlite_connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('tags', 'entry_tags') ORDER BY name"
        ).fetchall()
        assert version == (1,)
        assert row_count == (1,)
        assert tags_tables == [("entry_tags",), ("tags",)]
    finally:
        sqlite_connection.close()
