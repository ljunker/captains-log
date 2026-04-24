from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.attachments import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
    MAX_AUDIO_FILE_SIZE,
    MAX_IMAGE_FILE_SIZE,
    audio_mime_type_for_filename,
    build_storage_key,
    create_image_thumbnail,
    ensure_upload_directories,
    file_url,
    image_mime_type_for_filename,
    can_generate_thumbnail,
    storage_path,
    thumbnail_storage_key,
    thumbnail_url,
    is_raw_image,
)
from app.config import settings
from app.database import engine, get_db
from app.migration import run_migrations
from app.models import Attachment, Entry, Tag
from app.schemas import AttachmentRead, EntryCreate, EntryListResponse, EntryRead, EntrySearchResponse, EntryUpdate
from app.tags import normalize_tag_name
from app.timezone import APP_TIMEZONE, local_date


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
API_KEY_COOKIE_NAME = "captains_log_api_key"
INLINE_CSS = (BASE_DIR / "app" / "static" / "style.css").read_text(encoding="utf-8")


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations(engine)
    ensure_upload_directories()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Kleine Tagebuch-App mit Web-Oberfläche, SQLite-Speicher und CRUD-API.",
    version="0.1.0",
    lifespan=lifespan,
    root_path=settings.root_path,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    request_path = request.scope.get("path", request.url.path)
    if request_path.startswith("/static/") or request_path in {
        "/favicon.ico",
        "/manifest.webmanifest",
        "/service-worker.js",
        "/offline",
    }:
        return await call_next(request)

    configured_api_key = settings.api_key
    if not configured_api_key:
        return await call_next(request)

    header_key = request.headers.get("X-API-Key")
    cookie_key = request.cookies.get(API_KEY_COOKIE_NAME)
    query_key = request.query_params.get("api_key")

    if header_key == configured_api_key or cookie_key == configured_api_key or query_key == configured_api_key:
        response = await call_next(request)
        if query_key == configured_api_key and cookie_key != configured_api_key:
            response.set_cookie(
                API_KEY_COOKIE_NAME,
                configured_api_key,
                httponly=True,
                samesite="lax",
                path=settings.root_path or "/",
            )
        return response

    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Invalid or missing API key"})


@app.get("/", response_class=HTMLResponse, tags=["UI"], summary="Web-Oberfläche")
def read_home(request: Request) -> HTMLResponse:
    valid_query_key = settings.api_key and request.query_params.get("api_key") == settings.api_key
    query_suffix = f"?{urlencode({'api_key': settings.api_key})}" if valid_query_key else ""
    docs_path = f"{settings.root_path}/docs" if settings.root_path else "/docs"
    manifest_path = f"{settings.root_path}/manifest.webmanifest" if settings.root_path else "/manifest.webmanifest"
    service_worker_path = f"{settings.root_path}/service-worker.js" if settings.root_path else "/service-worker.js"
    apple_touch_icon_path = f"{settings.root_path}/static/apple-touch-icon.png" if settings.root_path else "/static/apple-touch-icon.png"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "root_path": settings.root_path,
            "docs_path": f"{docs_path}{query_suffix}",
            "inline_css": INLINE_CSS,
            "app_timezone": settings.timezone_name,
            "manifest_path": manifest_path,
            "service_worker_path": service_worker_path,
            "apple_touch_icon_path": apple_touch_icon_path,
        },
    )


@app.get("/manifest.webmanifest", include_in_schema=False)
def read_manifest() -> JSONResponse:
    root_path = settings.root_path or ""
    payload = {
        "name": settings.app_name,
        "short_name": "Captain's Log",
        "description": app.description,
        "start_url": f"{root_path}/" if root_path else "/",
        "scope": f"{root_path}/" if root_path else "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#fbfbf8",
        "theme_color": "#f5f5f2",
        "icons": [
            {
                "src": f"{root_path}/static/app-icon-192.png" if root_path else "/static/app-icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": f"{root_path}/static/app-icon-512.png" if root_path else "/static/app-icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }
    return JSONResponse(payload, media_type="application/manifest+json")


@app.get("/offline", include_in_schema=False)
def read_offline_page() -> HTMLResponse:
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Offline | Captain's Log</title>
            <style>
                body {
                    margin: 0;
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    padding: 24px;
                    background: linear-gradient(180deg, #f5f5f2 0%, #fbfbf8 100%);
                    color: #111111;
                    font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
                }
                main {
                    width: min(560px, 100%);
                    padding: 20px;
                    border: 1px solid rgba(17, 17, 17, 0.14);
                    background: rgba(255, 255, 255, 0.92);
                }
                p.eyebrow {
                    margin: 0 0 10px;
                    color: #8f1f1f;
                    font: 700 0.72rem/1 "Avenir Next", "Helvetica Neue", Arial, sans-serif;
                    letter-spacing: 0.18em;
                    text-transform: uppercase;
                }
                h1 {
                    margin: 0 0 8px;
                    font-size: 1.7rem;
                }
                p {
                    margin: 0;
                    color: #666666;
                    line-height: 1.5;
                }
            </style>
        </head>
        <body>
            <main>
                <p class="eyebrow">Offline</p>
                <h1>Captain's Log ist gerade offline.</h1>
                <p>Wenn du die Seite vorher schon geladen hattest, sollten zuletzt gecachte Inhalte weiterhin verfügbar sein.</p>
            </main>
        </body>
        </html>
        """
    )


@app.get("/service-worker.js", include_in_schema=False)
def read_service_worker() -> Response:
    service_worker_source = f"""
const CACHE_NAME = "captains-log-v1";
const ROOT_PATH = {json.dumps(settings.root_path or "")};
const APP_SHELL = [
  withRoot("/"),
  withRoot("/offline"),
  withRoot("/manifest.webmanifest"),
  withRoot("/static/apple-touch-icon.png"),
  withRoot("/static/app-icon-192.png"),
  withRoot("/static/app-icon-512.png")
];

function withRoot(path) {{
  return `${{ROOT_PATH}}${{path}}`;
}}

function isSameOrigin(requestUrl) {{
  return new URL(requestUrl).origin === self.location.origin;
}}

function isNavigationRequest(request) {{
  return request.mode === "navigate";
}}

function isApiCacheable(requestUrl) {{
  const pathname = new URL(requestUrl).pathname;
  return pathname.startsWith(withRoot("/api/entries")) || pathname.startsWith(withRoot("/api/search")) || pathname.startsWith(withRoot("/api/tags/suggestions"));
}}

function isStaticCacheable(requestUrl) {{
  const pathname = new URL(requestUrl).pathname;
  return (
    pathname === withRoot("/manifest.webmanifest") ||
    pathname === withRoot("/offline") ||
    pathname.startsWith(withRoot("/static/"))
  );
}}

self.addEventListener("install", (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(APP_SHELL.map((path) => new Request(path, {{credentials: "include"}})))
    )
  );
  self.skipWaiting();
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
}});

async function networkFirst(request, fallbackPath = null) {{
  const cache = await caches.open(CACHE_NAME);
  try {{
    const response = await fetch(request);
    if (request.method === "GET" && response.ok) {{
      cache.put(request, response.clone());
    }}
    return response;
  }} catch (error) {{
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {{
      return cachedResponse;
    }}
    if (fallbackPath) {{
      const fallbackResponse = await cache.match(fallbackPath);
      if (fallbackResponse) {{
        return fallbackResponse;
      }}
    }}
    throw error;
  }}
}}

async function staleWhileRevalidate(request) {{
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  const networkPromise = fetch(request)
    .then((response) => {{
      if (response.ok) {{
        cache.put(request, response.clone());
      }}
      return response;
    }})
    .catch(() => null);

  return cachedResponse || networkPromise || fetch(request);
}}

self.addEventListener("fetch", (event) => {{
  if (event.request.method !== "GET" || !isSameOrigin(event.request.url)) {{
    return;
  }}

  if (isNavigationRequest(event.request)) {{
    event.respondWith(networkFirst(event.request, withRoot("/offline")));
    return;
  }}

  if (isApiCacheable(event.request.url)) {{
    event.respondWith(networkFirst(event.request));
    return;
  }}

  if (isStaticCacheable(event.request.url)) {{
    event.respondWith(staleWhileRevalidate(event.request));
  }}
}});
"""
    return Response(service_worker_source, media_type="application/javascript")


@app.get("/health", tags=["System"], summary="Healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _get_all_entries(db: Session) -> list[Entry]:
    statement = (
        select(Entry)
        .options(selectinload(Entry.tags), selectinload(Entry.attachments))
        .order_by(Entry.created_at.asc(), Entry.id.asc())
    )
    return list(db.scalars(statement))


def _tag_names(entry: Entry) -> list[str]:
    return [tag.name for tag in entry.tags]


def _serialize_attachment(attachment: Attachment) -> AttachmentRead:
    return AttachmentRead.model_validate(
        {
            "id": attachment.id,
            "kind": attachment.kind,
            "original_filename": attachment.original_filename,
            "mime_type": attachment.mime_type,
            "file_size": attachment.file_size,
            "created_at": attachment.created_at,
            "thumbnail_url": thumbnail_url(attachment.id) if attachment.thumbnail_key else None,
            "file_url": file_url(attachment.id),
        }
    )


def _serialize_entry(entry: Entry) -> EntryRead:
    return EntryRead.model_validate(
        {
            "id": entry.id,
            "content": entry.content,
            "tags": _tag_names(entry),
            "attachments": [_serialize_attachment(attachment) for attachment in entry.attachments],
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }
    )


def _matches_tag(entry: Entry, selected_tag: str | None) -> bool:
    if selected_tag is None:
        return True
    return selected_tag in _tag_names(entry)


def _matches_search(entry: Entry, search_query: str | None) -> bool:
    if search_query is None:
        return True

    terms = [term for term in search_query.casefold().split() if term]
    if not terms:
        return True

    searchable_text = " ".join(
        [
            entry.content,
            " ".join(_tag_names(entry)),
            " ".join(attachment.original_filename for attachment in entry.attachments),
        ]
    ).casefold()
    return all(term in searchable_text for term in terms)


def _get_or_create_tags(tag_names: list[str], db: Session) -> list[Tag]:
    if not tag_names:
        return []

    existing_tags = {
        tag.name: tag
        for tag in db.scalars(select(Tag).where(Tag.name.in_(tag_names)))
    }
    tags: list[Tag] = []

    for tag_name in tag_names:
        tag = existing_tags.get(tag_name)
        if tag is None:
            tag = Tag(name=tag_name)
            db.add(tag)
            db.flush()
            existing_tags[tag_name] = tag
        tags.append(tag)

    return tags


def _delete_unused_tags(db: Session) -> None:
    unused_tags = list(
        db.scalars(
            select(Tag)
            .outerjoin(Tag.entries)
            .group_by(Tag.id)
            .having(func.count(Entry.id) == 0)
        )
    )
    for tag in unused_tags:
        db.delete(tag)


def _set_entry_tags(entry: Entry, tag_names: list[str], db: Session) -> None:
    entry.tags = _get_or_create_tags(tag_names, db)
    db.flush()
    _delete_unused_tags(db)


def _get_entry_or_404(entry_id: int, db: Session) -> Entry:
    entry = db.scalar(
        select(Entry)
        .options(selectinload(Entry.tags), selectinload(Entry.attachments))
        .where(Entry.id == entry_id)
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return entry


def _get_attachment_or_404(attachment_id: int, db: Session) -> Attachment:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return attachment


def _delete_attachment_files(attachment: Attachment) -> None:
    for storage_key in [attachment.storage_key, attachment.thumbnail_key]:
        if not storage_key:
            continue
        target = storage_path(storage_key)
        if target.exists():
            target.unlink()


def _attachment_kind_for_upload(upload: UploadFile) -> tuple[str, str]:
    provided_mime = (upload.content_type or "").lower()
    image_mime = image_mime_type_for_filename(upload.filename)
    if provided_mime in IMAGE_MIME_TYPES or image_mime is not None:
        return "image", provided_mime if provided_mime in IMAGE_MIME_TYPES else image_mime

    audio_mime = audio_mime_type_for_filename(upload.filename)
    if provided_mime in AUDIO_MIME_TYPES or audio_mime is not None:
        normalized_audio_mime = "audio/mp4" if provided_mime == "audio/x-m4a" else provided_mime
        return "audio", normalized_audio_mime if normalized_audio_mime in AUDIO_MIME_TYPES else audio_mime

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Unsupported attachment type. Allowed: JPEG, PNG, WebP, HEIC, HEIF, DNG, MP3, M4A, AAC, WAV.",
    )


def _read_upload_bytes(upload: UploadFile, max_file_size: int) -> bytes:
    payload = upload.file.read(max_file_size + 1)
    if len(payload) > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Attachment too large. Max size is {max_file_size // (1024 * 1024)} MB.",
        )
    if not payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Attachment must not be empty")
    return payload


def _store_attachment(entry: Entry, upload: UploadFile, db: Session) -> Attachment:
    kind, mime_type = _attachment_kind_for_upload(upload)
    max_file_size = MAX_IMAGE_FILE_SIZE if kind == "image" else MAX_AUDIO_FILE_SIZE
    payload = _read_upload_bytes(upload, max_file_size)
    original_key = build_storage_key("originals", upload.filename)
    original_path = storage_path(original_key)
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(payload)

    stored_thumbnail_key: str | None = None
    try:
        if kind == "image" and can_generate_thumbnail(upload.filename, mime_type):
            thumbnail_bytes = create_image_thumbnail(payload, upload.filename)
            stored_thumbnail_key = thumbnail_storage_key()
            thumbnail_path = storage_path(stored_thumbnail_key)
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            thumbnail_path.write_bytes(thumbnail_bytes)
    except Exception as exc:
        if is_raw_image(upload.filename):
            stored_thumbnail_key = None
        else:
            if original_path.exists():
                original_path.unlink()
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Image could not be processed") from exc

    attachment = Attachment(
        entry=entry,
        kind=kind,
        storage_key=original_key,
        thumbnail_key=stored_thumbnail_key,
        original_filename=upload.filename or "attachment",
        mime_type=mime_type,
        file_size=len(payload),
        sort_order=len(entry.attachments),
    )
    db.add(attachment)
    db.flush()
    return attachment


@app.get(
    "/api/tags/suggestions",
    response_model=list[str],
    tags=["Tags"],
    summary="Tag-Vorschläge laden",
)
def suggest_tags(
    query: str = Query(description="Beginn eines Tags für Autocomplete"),
    limit: int = Query(default=8, ge=1, le=20, description="Maximale Anzahl Vorschläge"),
    db: Session = Depends(get_db),
) -> list[str]:
    stripped_query = query.strip()
    statement = select(Tag.name).order_by(Tag.name.asc()).limit(limit)

    if stripped_query:
        normalized_query = normalize_tag_name(stripped_query)
        statement = (
            select(Tag.name)
            .where(Tag.name.startswith(normalized_query))
            .order_by(Tag.name.asc())
            .limit(limit)
        )

    return list(db.scalars(statement))


@app.get(
    "/api/entries",
    response_model=EntryListResponse,
    tags=["Entries"],
    summary="Einträge eines Tages laden",
)
def list_entries(
    day: date | None = Query(default=None, description="Optionales Tagesfilter im Format YYYY-MM-DD"),
    tag: str | None = Query(default=None, description="Optionaler Tag-Filter"),
    q: str | None = Query(default=None, description="Optionaler Volltext-Suchfilter"),
    db: Session = Depends(get_db),
) -> EntryListResponse:
    all_entries = _get_all_entries(db)
    try:
        selected_tag = normalize_tag_name(tag) if tag is not None and tag.strip() else None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    selected_search = q.strip() if q is not None and q.strip() else None
    matching_entries = [
        entry
        for entry in all_entries
        if _matches_tag(entry, selected_tag) and _matches_search(entry, selected_search)
    ]
    available_days = sorted({local_date(entry.created_at) for entry in matching_entries}, reverse=True)
    selected_day = day if day is not None else (available_days[0] if available_days else datetime.now(APP_TIMEZONE).date())
    day_entries = [entry for entry in all_entries if local_date(entry.created_at) == selected_day and _matches_search(entry, selected_search)]
    entries = [entry for entry in day_entries if _matches_tag(entry, selected_tag)]
    available_tags = sorted({tag_name for entry in day_entries for tag_name in _tag_names(entry)})

    previous_day = max((candidate for candidate in available_days if candidate < selected_day), default=None)
    next_day = min((candidate for candidate in available_days if candidate > selected_day), default=None)

    return EntryListResponse(
        day=selected_day,
        previous_day=previous_day,
        next_day=next_day,
        available_days=available_days,
        active_tag=selected_tag,
        active_search=selected_search,
        available_tags=available_tags,
        entries=[_serialize_entry(entry) for entry in entries],
    )


@app.get(
    "/api/search",
    response_model=EntrySearchResponse,
    tags=["Entries"],
    summary="Einträge global durchsuchen",
)
def search_entries(
    q: str = Query(description="Suchbegriff fuer Inhalt, Tags und Anhang-Dateinamen"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximale Anzahl Treffer"),
    db: Session = Depends(get_db),
) -> EntrySearchResponse:
    selected_search = q.strip()
    if not selected_search:
        return EntrySearchResponse(query="", results=[])

    matches = [
        entry
        for entry in sorted(_get_all_entries(db), key=lambda item: (item.created_at, item.id), reverse=True)
        if _matches_search(entry, selected_search)
    ][:limit]
    return EntrySearchResponse(
        query=selected_search,
        results=[
            {
                "day": local_date(entry.created_at),
                "entry": _serialize_entry(entry),
            }
            for entry in matches
        ],
    )


@app.post(
    "/api/entries",
    response_model=EntryRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Entries"],
    summary="Neuen Eintrag anlegen",
)
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)) -> EntryRead:
    entry = Entry(content=payload.content.strip())
    if payload.created_at is not None:
        entry.created_at = payload.created_at
        entry.updated_at = payload.created_at
    db.add(entry)
    db.flush()
    _set_entry_tags(entry, payload.tags, db)
    db.commit()
    return _serialize_entry(_get_entry_or_404(entry.id, db))


@app.get("/api/entries/{entry_id}", response_model=EntryRead, tags=["Entries"], summary="Eintrag laden")
def get_entry(entry_id: int, db: Session = Depends(get_db)) -> EntryRead:
    return _serialize_entry(_get_entry_or_404(entry_id, db))


@app.put("/api/entries/{entry_id}", response_model=EntryRead, tags=["Entries"], summary="Eintrag aktualisieren")
def update_entry(entry_id: int, payload: EntryUpdate, db: Session = Depends(get_db)) -> EntryRead:
    entry = _get_entry_or_404(entry_id, db)
    entry.content = payload.content.strip()
    _set_entry_tags(entry, payload.tags, db)
    db.add(entry)
    db.commit()
    return _serialize_entry(_get_entry_or_404(entry.id, db))


@app.delete(
    "/api/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Entries"],
    summary="Eintrag löschen",
)
def delete_entry(entry_id: int, db: Session = Depends(get_db)) -> Response:
    entry = _get_entry_or_404(entry_id, db)
    for attachment in list(entry.attachments):
        _delete_attachment_files(attachment)
    db.delete(entry)
    db.flush()
    _delete_unused_tags(db)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/entries/{entry_id}/attachments",
    response_model=list[AttachmentRead],
    status_code=status.HTTP_201_CREATED,
    tags=["Attachments"],
    summary="Anhänge zu einem Eintrag hochladen",
)
def upload_attachments(
    entry_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> list[AttachmentRead]:
    entry = _get_entry_or_404(entry_id, db)
    created_attachments: list[Attachment] = []
    try:
        for upload in files:
            created_attachments.append(_store_attachment(entry, upload, db))
        db.commit()
    except Exception:
        db.rollback()
        for attachment in created_attachments:
            _delete_attachment_files(attachment)
        raise
    return [_serialize_attachment(attachment) for attachment in created_attachments]


@app.get(
    "/api/attachments/{attachment_id}/file",
    tags=["Attachments"],
    summary="Originaldatei eines Anhangs laden",
)
def get_attachment_file(attachment_id: int, db: Session = Depends(get_db)) -> FileResponse:
    attachment = _get_attachment_or_404(attachment_id, db)
    target = storage_path(attachment.storage_key)
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found")
    return FileResponse(
        target,
        media_type=attachment.mime_type,
        filename=attachment.original_filename,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.get(
    "/api/attachments/{attachment_id}/thumbnail",
    tags=["Attachments"],
    summary="Thumbnail eines Bildanhangs laden",
)
def get_attachment_thumbnail(attachment_id: int, db: Session = Depends(get_db)) -> FileResponse:
    attachment = _get_attachment_or_404(attachment_id, db)
    if attachment.thumbnail_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment thumbnail not found")
    target = storage_path(attachment.thumbnail_key)
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment thumbnail not found")
    return FileResponse(target, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@app.delete(
    "/api/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Attachments"],
    summary="Anhang löschen",
)
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)) -> Response:
    attachment = _get_attachment_or_404(attachment_id, db)
    _delete_attachment_files(attachment)
    db.delete(attachment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
