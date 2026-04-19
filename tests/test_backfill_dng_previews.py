from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def test_backfill_dng_previews_creates_missing_thumbnail(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "test.db"
    uploads_path = tmp_path / "uploads"
    os.environ["SQLITE_PATH"] = str(sqlite_path)
    os.environ["UPLOADS_PATH"] = str(uploads_path)
    os.environ["API_KEY"] = "test-key"
    os.environ["APP_TIMEZONE"] = "UTC"

    for module_name in [
        "app.config",
        "app.database",
        "app.migration",
        "app.models",
        "app.attachments",
        "app.backfill_dng_previews",
    ]:
        sys.modules.pop(module_name, None)

    attachments_module = importlib.import_module("app.attachments")
    database_module = importlib.import_module("app.database")
    migration_module = importlib.import_module("app.migration")
    models_module = importlib.import_module("app.models")
    backfill_module = importlib.import_module("app.backfill_dng_previews")

    migration_module.run_migrations(database_module.engine)
    attachments_module.ensure_upload_directories()

    original_key = "originals/example.dng"
    original_path = uploads_path / original_key
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(b"fake-dng")

    db = database_module.SessionLocal()
    try:
        entry = models_module.Entry(content="Mit RAW")
        db.add(entry)
        db.flush()
        attachment = models_module.Attachment(
            entry_id=entry.id,
            kind="image",
            storage_key=original_key,
            thumbnail_key=None,
            original_filename="IMG_1652.DNG",
            mime_type="image/x-adobe-dng",
            file_size=8,
            sort_order=0,
        )
        db.add(attachment)
        db.commit()
    finally:
        db.close()

    def fake_create_image_thumbnail(source_bytes: bytes, filename: str | None = None) -> bytes:
        assert source_bytes == b"fake-dng"
        assert filename == "IMG_1652.DNG"
        return b"jpeg-preview"

    attachments_module.create_image_thumbnail = fake_create_image_thumbnail

    result = backfill_module.run_backfill()
    assert result.processed == 1
    assert result.failed == 0

    db = database_module.SessionLocal()
    try:
        attachment = db.scalar(importlib.import_module("sqlalchemy").select(models_module.Attachment))
        assert attachment is not None
        assert attachment.thumbnail_key is not None
        thumbnail_path = uploads_path / attachment.thumbnail_key
        assert thumbnail_path.read_bytes() == b"jpeg-preview"
    finally:
        db.close()


def test_backfill_dng_previews_dry_run_does_not_write(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "test.db"
    uploads_path = tmp_path / "uploads"
    os.environ["SQLITE_PATH"] = str(sqlite_path)
    os.environ["UPLOADS_PATH"] = str(uploads_path)
    os.environ["API_KEY"] = "test-key"
    os.environ["APP_TIMEZONE"] = "UTC"

    for module_name in [
        "app.config",
        "app.database",
        "app.migration",
        "app.models",
        "app.attachments",
        "app.backfill_dng_previews",
    ]:
        sys.modules.pop(module_name, None)

    attachments_module = importlib.import_module("app.attachments")
    database_module = importlib.import_module("app.database")
    migration_module = importlib.import_module("app.migration")
    models_module = importlib.import_module("app.models")
    backfill_module = importlib.import_module("app.backfill_dng_previews")

    migration_module.run_migrations(database_module.engine)
    attachments_module.ensure_upload_directories()

    original_key = "originals/example.dng"
    original_path = uploads_path / original_key
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(b"fake-dng")

    db = database_module.SessionLocal()
    try:
        entry = models_module.Entry(content="Mit RAW")
        db.add(entry)
        db.flush()
        attachment = models_module.Attachment(
            entry_id=entry.id,
            kind="image",
            storage_key=original_key,
            thumbnail_key=None,
            original_filename="IMG_1652.DNG",
            mime_type="image/x-adobe-dng",
            file_size=8,
            sort_order=0,
        )
        db.add(attachment)
        db.commit()
    finally:
        db.close()

    attachments_module.create_image_thumbnail = lambda source_bytes, filename=None: b"jpeg-preview"

    result = backfill_module.run_backfill(dry_run=True)
    assert result.processed == 1
    assert result.failed == 0

    db = database_module.SessionLocal()
    try:
        attachment = db.scalar(importlib.import_module("sqlalchemy").select(models_module.Attachment))
        assert attachment is not None
        assert attachment.thumbnail_key is None
    finally:
        db.close()
