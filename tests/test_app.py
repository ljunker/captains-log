from __future__ import annotations

import importlib
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image


def png_payload() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "#336699").save(buffer, format="PNG")
    return buffer.getvalue()


def test_entry_crud_flow(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "test.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)
    os.environ["UPLOADS_PATH"] = str(tmp_path / "uploads")
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

        manifest_response = client.get("/manifest.webmanifest")
        assert manifest_response.status_code == 200
        assert manifest_response.headers["content-type"].startswith("application/manifest+json")
        assert manifest_response.json()["display"] == "standalone"

        service_worker_response = client.get("/service-worker.js")
        assert service_worker_response.status_code == 200
        assert service_worker_response.headers["content-type"].startswith("application/javascript")
        assert "captains-log-v1" in service_worker_response.text

        offline_response = client.get("/offline")
        assert offline_response.status_code == 200
        assert "Captain's Log ist gerade offline" in offline_response.text

        today = datetime.now(UTC).replace(microsecond=0)
        yesterday = today - timedelta(days=1)

        db = database_module.SessionLocal()
        older_entry = models_module.Entry(content="Gestern")
        older_entry.created_at = yesterday
        older_entry.updated_at = yesterday
        db.add(older_entry)
        db.commit()
        db.close()

        custom_created_at = today.replace(hour=9, minute=15, second=0)

        create_response = client.post(
            "/api/entries",
            json={
                "content": "Erster Eintrag",
                "tags": ["Arbeit", "Python", "arbeit"],
                "created_at": custom_created_at.isoformat(),
            },
            headers=headers,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        entry_id = created["id"]
        assert created["created_at"] == custom_created_at.isoformat()
        assert created["tags"] == ["arbeit", "python"]
        assert created["attachments"] == []

        upload_response = client.post(
                f"/api/entries/{entry_id}/attachments",
                headers=headers,
                files=[
                    ("files", ("iphone-shot.dng", b"raw-dng-payload", "image/x-adobe-dng")),
                    ("files", ("iphone-shot.heic", png_payload(), "image/png")),
                    ("files", ("memo.m4a", b"audio-test", "audio/mp4")),
                ],
            )
        assert upload_response.status_code == 201
        attachments = upload_response.json()
        assert len(attachments) == 3
        assert [attachment["kind"] for attachment in attachments] == ["image", "image", "audio"]
        assert attachments[0]["thumbnail_url"] is None
        assert attachments[1]["thumbnail_url"].endswith("/thumbnail")
        assert attachments[2]["thumbnail_url"] is None
        raw_attachment_id = attachments[0]["id"]
        image_attachment_id = attachments[1]["id"]
        audio_attachment_id = attachments[2]["id"]

        list_response = client.get("/api/entries", headers=headers)
        assert list_response.status_code == 200
        listed = list_response.json()
        assert listed["day"] == custom_created_at.date().isoformat()
        assert listed["previous_day"] == yesterday.date().isoformat()
        assert listed["next_day"] is None
        assert listed["active_tag"] is None
        assert listed["active_search"] is None
        assert listed["available_tags"] == ["arbeit", "python"]
        assert len(listed["entries"]) == 1
        assert [attachment["kind"] for attachment in listed["entries"][0]["attachments"]] == ["image", "image", "audio"]

        content_search_response = client.get("/api/entries?q=erster", headers=headers)
        assert content_search_response.status_code == 200
        content_search_payload = content_search_response.json()
        assert content_search_payload["active_search"] == "erster"
        assert len(content_search_payload["entries"]) == 1
        assert content_search_payload["entries"][0]["id"] == entry_id

        tag_search_response = client.get("/api/entries?q=python", headers=headers)
        assert tag_search_response.status_code == 200
        assert tag_search_response.json()["entries"][0]["tags"] == ["arbeit", "python"]

        attachment_search_response = client.get("/api/entries?q=memo", headers=headers)
        assert attachment_search_response.status_code == 200
        assert attachment_search_response.json()["entries"][0]["id"] == entry_id

        missing_search_response = client.get("/api/entries?q=kommt-nicht-vor", headers=headers)
        assert missing_search_response.status_code == 200
        assert missing_search_response.json()["active_search"] == "kommt-nicht-vor"
        assert missing_search_response.json()["entries"] == []

        filtered_response = client.get("/api/entries?tag=python", headers=headers)
        assert filtered_response.status_code == 200
        filtered_payload = filtered_response.json()
        assert filtered_payload["active_tag"] == "python"
        assert filtered_payload["active_search"] is None
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
        assert len(update_response.json()["attachments"]) == 3

        raw_file_response = client.get(f"/api/attachments/{raw_attachment_id}/file", headers=headers)
        assert raw_file_response.status_code == 200
        assert raw_file_response.headers["content-type"].startswith("image/x-adobe-dng")

        raw_thumbnail_response = client.get(f"/api/attachments/{raw_attachment_id}/thumbnail", headers=headers)
        assert raw_thumbnail_response.status_code == 404

        thumbnail_response = client.get(f"/api/attachments/{image_attachment_id}/thumbnail", headers=headers)
        assert thumbnail_response.status_code == 200
        assert thumbnail_response.headers["content-type"].startswith("image/jpeg")

        image_file_response = client.get(f"/api/attachments/{image_attachment_id}/file", headers=headers)
        assert image_file_response.status_code == 200
        assert image_file_response.headers["content-type"].startswith("image/png")

        audio_file_response = client.get(f"/api/attachments/{audio_attachment_id}/file", headers=headers)
        assert audio_file_response.status_code == 200
        assert audio_file_response.headers["content-type"].startswith("audio/mp4")

        delete_attachment_response = client.delete(f"/api/attachments/{audio_attachment_id}", headers=headers)
        assert delete_attachment_response.status_code == 204

        refreshed_entry_response = client.get(f"/api/entries/{entry_id}", headers=headers)
        assert refreshed_entry_response.status_code == 200
        assert [attachment["kind"] for attachment in refreshed_entry_response.json()["attachments"]] == ["image", "image"]

        missing_tag_response = client.get("/api/entries?tag=python", headers=headers)
        assert missing_tag_response.status_code == 200
        assert missing_tag_response.json()["entries"] == []

        previous_day_response = client.get(f"/api/entries?day={yesterday.date().isoformat()}", headers=headers)
        assert previous_day_response.status_code == 200
        previous_day_payload = previous_day_response.json()
        assert previous_day_payload["day"] == yesterday.date().isoformat()
        assert previous_day_payload["next_day"] == today.date().isoformat()
        assert previous_day_payload["active_search"] is None
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
        attachment_count = sqlite_connection.execute("SELECT COUNT(*) FROM attachments").fetchone()
        assert version == (2,)
        assert tags == []
        assert attachment_count == (0,)
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
    os.environ["UPLOADS_PATH"] = str(tmp_path / "uploads")
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
        assert payload["active_search"] is None

    sqlite_connection = sqlite3.connect(sqlite_path)
    try:
        version = sqlite_connection.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        row_count = sqlite_connection.execute("SELECT COUNT(*) FROM entries").fetchone()
        tags_tables = sqlite_connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('attachments', 'tags', 'entry_tags') ORDER BY name"
        ).fetchall()
        assert version == (2,)
        assert row_count == (1,)
        assert tags_tables == [("attachments",), ("entry_tags",), ("tags",)]
    finally:
        sqlite_connection.close()
