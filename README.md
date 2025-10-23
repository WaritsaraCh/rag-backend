RAG Project Backend

Overview
- Organized Flask backend with clear module boundaries for API, database, auth, utils, config, and migrations.

Structure
- api/: Flask blueprints and route registration
  - routes.py: Defines `api_bp` and endpoints (`/`, `/chat`, `/add-document`), plus `register_routes(app)`
- app.py: Application entry; loads config, CORS, registers routes, runs server
- auth/: User management
  - user_manager.py: Create/authenticate users, update profiles, fetch conversations
  - cli.py: CLI to create/list/auth users
- config/: Centralized settings
  - settings.py: `get_config()` and environment-specific settings
- database/: DB access and operations
  - operations.py: Connection pool, helpers, and core DB functions
  - schema01.sql: Base schema (documents, chunks, conversations, messages)
- migrations/: SQL migrations and runner
  - 001_add_users_table.sql: Users table, FKs, triggers, optional view
  - runner.py: Executes migrations using `config.settings`
- utils/: Supporting modules
  - document_loaders.py: Load content from `.txt` and `.pdf`
  - llm.py: Generate answers, iPhone info fetcher

Setup
- Create `.env` at `backend/.env` (or set environment variables):
  - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
  - FLASK_HOST, FLASK_PORT, FLASK_DEBUG
  - OLLAMA_HOST, OLLAMA_MODEL (optional)
- Alternatively, adjust defaults in `config/settings.py`.

Run Server
- From `backend/`: `python app.py`
- Endpoints:
  - `GET /` → health
  - `POST /chat` → body: `{ "question": "...", "session_id": "..." }`
  - `POST /add-document` → multipart file upload or JSON `{ title, sourceType, sourceUrl, category, version, content }`

Migrations
- Check and run users migration:
  - `python migrations/runner.py`

User CLI
- Create: `python auth/cli.py create --username alice --email alice@example.com --admin`
- List: `python auth/cli.py list`
- Auth: `python auth/cli.py auth --username alice`

Notes
- `database/operations.py` uses a connection pool configured via `config.settings`.
- `api/routes.py` is a Blueprint registered in `app.py`.
- Ensure PostgreSQL is running and accessible by the configured credentials.