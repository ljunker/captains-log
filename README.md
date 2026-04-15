# Captain's Log

Kleines Python-Tagebuchprojekt mit:

- Web-Oberfläche zum Betrachten und Bearbeiten von Einträgen
- JSON-CRUD-API unter `/api/entries`
- Swagger-Doku unter `/docs`
- SQLite als persistenter Datenspeicher
- API-Key-Schutz per `API_KEY`-Umgebungsvariable
- lokalem Start für PyCharm-Debugging
- Docker- und Compose-Setup für die App
- Beispielkonfiguration für vorgeschalteten Server-`nginx`

## Lokal starten

```bash
uv sync
uv run python main.py
```

Danach ist die Anwendung unter [http://127.0.0.1:8000](http://127.0.0.1:8000) erreichbar.

Wenn `API_KEY` gesetzt ist, rufst du UI und Swagger z. B. so auf:

```text
http://127.0.0.1:8000/?api_key=dein-schluessel
http://127.0.0.1:8000/docs?api_key=dein-schluessel
```

Alternativ für Auto-Reload während der Entwicklung:

```bash
uv run uvicorn app.main:app --reload
```

## PyCharm-Debugging

Lege in PyCharm eine normale Python-Run-Configuration an:

- Script path: `/Users/lj/PycharmProjects/captains_log/main.py`
- Working directory: `/Users/lj/PycharmProjects/captains_log`
- Python interpreter: `/Users/lj/PycharmProjects/captains_log/.venv/bin/python`

`main.py` startet Uvicorn ohne Reload, damit der Debugger sauber anhängt.

Optional kannst du in der Run-Configuration noch `API_KEY=dein-schluessel` als Environment Variable setzen.

## API

```text
GET    /api/entries
POST   /api/entries
GET    /api/entries/{id}
PUT    /api/entries/{id}
DELETE /api/entries/{id}
GET    /health
GET    /docs
GET    /openapi.json
```

Die Swagger-UI ist unter [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) verfügbar.

Die API akzeptiert den Schlüssel per `X-API-Key`-Header. Für Browserzugriff auf UI und Swagger kann der Schlüssel einmalig als Query-Parameter `api_key` übergeben werden; danach wird ein Cookie gesetzt.

Beispiel für einen neuen Eintrag:

```bash
curl -X POST http://127.0.0.1:8000/api/entries \
  -H "X-API-Key: dein-schluessel" \
  -H "Content-Type: application/json" \
  -d '{"content":"Erster Testeintrag"}'
```

## Datenbank-Migrationen

Beim App-Start wird die SQLite-Datenbank versioniert.

- Die Versionsnummer liegt in der Tabelle `schema_version`.
- SQL-Migrationen liegen unter [`app/migrations`](/Users/lj/PycharmProjects/captains_log/app/migrations).
- `000_initial.sql` beschreibt den initialen Tabellenstand.
- Bestehende Datenbanken ohne `schema_version` werden beim ersten Start übernommen und auf Version `0` gesetzt.

## Docker Compose

```bash
chmod +x ./dockerhub-up
./dockerhub-up
```

Das Deployment zieht das veröffentlichte Docker-Hub-Image `kryptikker/captains-log` und startet es per `docker compose`. Die Version wird in dieser Reihenfolge bestimmt:

- Argument `--version`
- Umgebungsvariable `DOCKER_IMAGE_VERSION`
- [`version.txt`](/Users/lj/PycharmProjects/captains_log/version.txt)
- Fallback `latest`

Zusätzlich prüft das Script die neuesten Docker-Hub-Tags und warnt, wenn eine gepinnte Version hinter der neuesten verfügbaren Version liegt.

Nützliche Varianten:

```bash
./dockerhub-up --check-only
./dockerhub-up --version 1.2.0
./dockerhub-up --sync-version-file
```

Standardmäßig bindet der Container nur lokal auf dem Host unter [http://127.0.0.1:8000](http://127.0.0.1:8000). Einen anderen lokalen Port kannst du so setzen:

```bash
API_KEY=dein-schluessel HOST_PORT=8010 ./dockerhub-up
```

Die SQLite-Datei liegt im benannten Volume `captains_log_data`.

## Reverse Proxy auf dem Server

Wenn auf deinem Server bereits `nginx` läuft, lass Compose nur die App starten und leite im Host-`nginx` auf `127.0.0.1:8000` weiter.

Eine passende Beispielkonfiguration liegt in [nginx/default.conf](/Users/lj/PycharmProjects/captains_log/nginx/default.conf).

Wichtige Punkte:

- In `server_name` deine echte Domain eintragen
- Optional TLS/Let's Encrypt in deiner bestehenden `nginx`-Struktur ergänzen
- Falls du `HOST_PORT` änderst, auch `proxy_pass` entsprechend anpassen

## Git Tags

Für semantische Release-Tags gibt es das Script [`./createtag`](/Users/lj/PycharmProjects/captains_log/createtag).

```bash
chmod +x ./createtag
./createtag patch
./createtag minor
./createtag major
./createtag v1.2.0
./createtag --dry-run minor
```

Das Script berechnet bei `patch`/`minor`/`major` die nächste lokale Version anhand der vorhandenen `vX.Y.Z`-Tags und erstellt einen annotierten Tag. Den Push machst du danach separat von Hand.
