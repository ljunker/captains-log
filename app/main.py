from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.migration import run_migrations
from app.models import Entry
from app.schemas import EntryCreate, EntryListResponse, EntryRead, EntryUpdate
from app.timezone import APP_TIMEZONE, local_date


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
API_KEY_COOKIE_NAME = "captains_log_api_key"
INLINE_CSS = (BASE_DIR / "app" / "static" / "style.css").read_text(encoding="utf-8")


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations(engine)
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
    if request.url.path.startswith("/static/") or request.url.path == "/favicon.ico":
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

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "root_path": settings.root_path,
            "docs_path": f"{docs_path}{query_suffix}",
            "inline_css": INLINE_CSS,
            "app_timezone": settings.timezone_name,
        },
    )


@app.get("/health", tags=["System"], summary="Healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _get_all_entries(db: Session) -> list[Entry]:
    statement = select(Entry).order_by(Entry.created_at.asc(), Entry.id.asc())
    return list(db.scalars(statement))


@app.get(
    "/api/entries",
    response_model=EntryListResponse,
    tags=["Entries"],
    summary="Einträge eines Tages laden",
)
def list_entries(
    day: date | None = Query(default=None, description="Optionales Tagesfilter im Format YYYY-MM-DD"),
    db: Session = Depends(get_db),
) -> EntryListResponse:
    all_entries = _get_all_entries(db)
    available_days = sorted({local_date(entry.created_at) for entry in all_entries}, reverse=True)
    selected_day = day if day is not None else (available_days[0] if available_days else datetime.now(APP_TIMEZONE).date())
    entries = [entry for entry in all_entries if local_date(entry.created_at) == selected_day]

    previous_day = max((candidate for candidate in available_days if candidate < selected_day), default=None)
    next_day = min((candidate for candidate in available_days if candidate > selected_day), default=None)

    return EntryListResponse(
        day=selected_day,
        previous_day=previous_day,
        next_day=next_day,
        entries=entries,
    )


@app.post(
    "/api/entries",
    response_model=EntryRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Entries"],
    summary="Neuen Eintrag anlegen",
)
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)) -> Entry:
    entry = Entry(content=payload.content.strip())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _get_entry_or_404(entry_id: int, db: Session) -> Entry:
    entry = db.get(Entry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return entry


@app.get("/api/entries/{entry_id}", response_model=EntryRead, tags=["Entries"], summary="Eintrag laden")
def get_entry(entry_id: int, db: Session = Depends(get_db)) -> Entry:
    return _get_entry_or_404(entry_id, db)


@app.put("/api/entries/{entry_id}", response_model=EntryRead, tags=["Entries"], summary="Eintrag aktualisieren")
def update_entry(entry_id: int, payload: EntryUpdate, db: Session = Depends(get_db)) -> Entry:
    entry = _get_entry_or_404(entry_id, db)
    entry.content = payload.content.strip()
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.delete(
    "/api/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Entries"],
    summary="Eintrag löschen",
)
def delete_entry(entry_id: int, db: Session = Depends(get_db)) -> Response:
    entry = _get_entry_or_404(entry_id, db)
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
