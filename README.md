# El Malick Gest

Desktop application for managing a Senegalese school — from primary (CI–CM2)
through middle (6ème–3ème) and high school (2nde–Terminale). Built with
**PyQt6** and **PostgreSQL**.

It covers student records, grades and bulletins (report cards), attendance,
discipline, staff, finance (payments, dues, expenses), inventory, timetables,
analytics, and a parent portal exposed through an optional REST API.

---

## Requirements

- **Python 3.10+** (3.12 recommended)
- **PostgreSQL 12+**
- **PostgreSQL client tools** (`pg_dump`, `psql`, `pg_restore`) on your `PATH` —
  required for the automatic backup/restore feature.

## Installation

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd "El Malick Gest"

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. Install dependencies (desktop app)
pip install -r requirements.txt
# Optional — only if you run the REST API as well:
pip install -r requirements_api.txt
```

## Database setup

1. Create an empty PostgreSQL database, e.g. `elmalick_db`:

   ```bash
   createdb -U postgres elmalick_db
   ```

2. Create your local configuration from the template and edit it:

   ```bash
   cp config.ini.example config.ini
   ```

   Set the `[DATABASE]` section (`host`, `port`, `dbname`, `user`). The database
   password is read from the OS keyring or the `PGPASSWORD` environment variable —
   it is **not** stored in `config.ini`.

3. Set up the schema. Run the bootstrap once — it creates all tables and brings
   the migrations to head (works on an empty database; safe to re-run):

   ```bash
   .venv/Scripts/python setup_database.py     # Windows
   .venv/bin/python setup_database.py          # Linux/macOS
   ```

   On an existing database that is already initialised, applying only new
   migrations is enough:

   ```bash
   .venv/Scripts/python -m alembic upgrade head
   ```

   > Note: `alembic upgrade head` alone cannot build a *clean* database from
   > scratch — the table-creating step lives in `db_schema`, so use
   > `setup_database.py` for a fresh install. The current head is revision **010**.

## Configuration & secrets

- `config.ini` is **git-ignored** — never commit it. Use `config.ini.example`
  as the template.
- `[SECURITY] fernet_key` is auto-generated on first run and used to encrypt
  secrets at rest. Keep it private; do not commit it.
- For the REST API, set a strong JWT secret before running in production:

  ```bash
  export ELMALICK_API_SECRET="<a-long-random-string>"
  export ELMALICK_ENV="production"   # makes the API refuse to start with the default secret
  ```

## Running

### Desktop application

```bash
.venv/Scripts/python main_dashbord.py     # Windows
.venv/bin/python main_dashbord.py          # Linux/macOS
```

On first run a setup wizard helps create the initial admin account. Log in with
that account; roles (Admin, Comptable, Secrétaire, Pédagogique, Prof, parent)
control which modules and actions are available (see `services/authorization.py`).

### REST API (optional — parent portal)

```bash
.venv/Scripts/uvicorn api.main:app --port 8000
```

## Backups

Backups use `pg_dump` and are scheduled automatically when
`[DATABASE] auto_backup = True`. `.sql` dumps are restored atomically with
`psql --single-transaction`; custom-format `.backup` files use `pg_restore -1`.
Ensure the PostgreSQL client tools are on your `PATH`.

## Tests

```bash
.venv/Scripts/python -m pytest          # full suite
.venv/Scripts/python -m pytest --cov    # with coverage
```

## Project layout

| Path | Purpose |
|------|---------|
| `main_dashbord.py` | Application entry point (main window, module loader) |
| `*_management.py`, `*_dashboard.py`, … | PyQt6 module windows (UI) |
| `services/` | Pure business rules (grades, finance, attendance, RBAC) — no SQL |
| `src/data/` | Data-access layer (repositories) — all SQL lives here |
| `repositories/` | Thin compatibility shims re-exporting `src/data/*` |
| `api/` | FastAPI app for the parent portal |
| `alembic/` | Database migrations (schema source of truth) |
| `tests/` | pytest suite |

## Packaging

The app is packaged for distribution with PyInstaller. See
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the full release procedure and
[RUNBOOK.md](RUNBOOK.md) for deployment/upgrade steps.
