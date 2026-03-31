from __future__ import annotations

import importlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


def test_entry_crud_flow(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "test.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)
    os.environ["API_KEY"] = "test-key"

    for module_name in ["app.config", "app.database", "app.models", "app.main"]:
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
            json={"content": "Erster Eintrag"},
            headers=headers,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        entry_id = created["id"]

        list_response = client.get("/api/entries", headers=headers)
        assert list_response.status_code == 200
        listed = list_response.json()
        assert listed["day"] == today.date().isoformat()
        assert listed["previous_day"] == yesterday.date().isoformat()
        assert listed["next_day"] is None
        assert len(listed["entries"]) == 1

        update_response = client.put(
            f"/api/entries/{entry_id}",
            json={"content": "Aktualisiert"},
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["content"] == "Aktualisiert"

        previous_day_response = client.get(f"/api/entries?day={yesterday.date().isoformat()}", headers=headers)
        assert previous_day_response.status_code == 200
        previous_day_payload = previous_day_response.json()
        assert previous_day_payload["day"] == yesterday.date().isoformat()
        assert previous_day_payload["next_day"] == today.date().isoformat()
        assert len(previous_day_payload["entries"]) == 1

        delete_response = client.delete(f"/api/entries/{entry_id}", headers=headers)
        assert delete_response.status_code == 204

        missing_response = client.get(f"/api/entries/{entry_id}", headers=headers)
        assert missing_response.status_code == 404
