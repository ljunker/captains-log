from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import or_, select

from app import attachments
from app.database import SessionLocal, engine
from app.migration import run_migrations
from app.models import Attachment


@dataclass
class BackfillResult:
    processed: int = 0
    skipped: int = 0
    failed: int = 0


def run_backfill(*, dry_run: bool = False, limit: int | None = None) -> BackfillResult:
    run_migrations(engine)
    attachments.ensure_upload_directories()
    result = BackfillResult()

    db = SessionLocal()
    try:
        statement = (
            select(Attachment)
            .where(Attachment.kind == "image")
            .where(Attachment.thumbnail_key.is_(None))
            .where(
                or_(
                    Attachment.mime_type.in_(["image/x-adobe-dng", "image/dng"]),
                    Attachment.original_filename.ilike("%.dng"),
                )
            )
            .order_by(Attachment.id.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)

        candidates = list(db.scalars(statement))
        for attachment in candidates:
            original_path = attachments.storage_path(attachment.storage_key)
            if not original_path.exists():
                result.failed += 1
                continue

            try:
                thumbnail_bytes = attachments.create_image_thumbnail(
                    original_path.read_bytes(),
                    attachment.original_filename,
                )
            except Exception:
                result.failed += 1
                continue

            result.processed += 1
            if dry_run:
                continue

            storage_key = attachments.thumbnail_storage_key()
            thumbnail_path = attachments.storage_path(storage_key)
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            thumbnail_path.write_bytes(thumbnail_bytes)
            attachment.thumbnail_key = storage_key
            db.add(attachment)

        if dry_run:
            db.rollback()
        else:
            db.commit()

        result.skipped = max(0, len(candidates) - result.processed - result.failed)
        return result
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Erzeugt JPEG-Previews fuer bestehende DNG-Anhaenge.")
    parser.add_argument("--dry-run", action="store_true", help="Nur pruefen, nichts schreiben.")
    parser.add_argument("--limit", type=int, default=None, help="Optional nur die ersten N Treffer verarbeiten.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = run_backfill(dry_run=args.dry_run, limit=args.limit)
    print(
        f"processed={result.processed} skipped={result.skipped} failed={result.failed}"
        + (" dry_run=true" if args.dry_run else "")
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
