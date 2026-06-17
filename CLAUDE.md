# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

`live-rail` is a unified Dash dashboard for managing and visualizing photometric redshift (photo-z) estimation data from the LSST DESC RAIL framework. It provides CRUD management of catalog entities, estimation workflow execution, and interactive visualization — all backed by the `pz-rail-svc` package for data access.

## Build & Development Commands

```bash
# Install in development mode
pip install -e '.[dev]'

# Run the dashboard (local DB)
live-rail dashboard --backend local --db-url "sqlite+aiosqlite:///rail_svc.db"

# Run unit tests (excludes integration tests)
pytest

# Run integration tests (requires real DB + data files)
pytest tests/test_integration.py -m integration -v

# Run all tests together
pytest -m "integration or not integration"

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/

# Pylint
pylint src/live_rail/ --rcfile=pyproject.toml
```

## Architecture

```
src/live_rail/
├── app.py                    # Direct entry point (python -m live_rail.app)
├── rail_svc_utils.py         # Database setup helpers (safe_insert_*)
├── backend/
│   └── provider.py           # BackendProvider singleton — switches local_sync/remote_sync
├── cli/
│   └── commands.py           # Click CLI with 'dashboard' command
├── wrappers/
│   ├── object_wrapper.py     # ObjectWrapper, CatalogWrapper, MultiCatalogWrapper ABCs
│   └── rail_svc_wrapper.py   # RailSvcLocal/RemoteCatalogWrapper implementations
└── dashboard/
    ├── app.py                # Dash app factory (create_app, use_pages=True)
    ├── layout.py             # Top-level layout: sidebar + page_container + logo
    ├── nav.py                # Sidebar navigation
    └── pages/
        ├── home.py           # Landing page with connection status
        ├── settings.py       # Backend mode/URL configuration
        ├── crud/
        │   ├── _base.py      # CrudPageConfig + register_crud_callbacks factory
        │   ├── _components.py # AG Grid table, form builders, modals
        │   └── *.py          # One file per entity (algorithm, dataset, etc.)
        ├── estimation/       # Estimate PDF, Ensemble, Dataset pages
        └── visualizers/      # Single + Multi catalog interactive visualizers
```

### Key Design Patterns

- **BackendProvider singleton** (`backend/provider.py`): All data access goes through `BackendProvider.get()` which dispatches to `rail_svc.local_sync` or `rail_svc.remote_sync` based on settings.
- **CRUD page factory** (`pages/crud/_base.py`): `register_crud_callbacks(config)` generates all callbacks from a `CrudPageConfig` dataclass. Each entity page is ~15 lines.
- **AG Grid tables**: Using `dash-ag-grid` with `cellClicked` for detail popups and FK lookups.
- **Wrapper caching**: Visualizer pages cache `RailSvcLocalCatalogWrapper` instances per dataset_id to avoid re-initialization on every callback.
- **Dash Pages**: Multi-page app with `use_pages=True`. Pages auto-register via `dash.register_page()` at module import time.

## Configuration

- `--backend local|remote` — which rail_svc backend to use
- `--db-url` — SQLite URL for local mode (default: `sqlite+aiosqlite:///rail_svc.db`)
- `--server-url` — FastAPI server URL for remote mode
- `--catalog-yaml` — RAIL catalog YAML config (default: `nb/sandbox_catalogs.yaml`)

## Testing

- Unit tests mock all `rail_svc` dependencies and run in <2s
- Integration tests require `rail_svc.db` + `nb/sandbox_catalogs.yaml` + HDF5 data files
- Integration tests are marked with `@pytest.mark.integration` and excluded from default runs
- Dash page modules can't be imported at top level in tests (triggers `register_page` error) — import inside test methods after creating a Dash app

## Code Style

- Line length: 110 (ruff + pylint)
- Ruff with E, F, W, I rules (includes isort)
- mypy with `disallow_untyped_defs = false` (Dash callbacks are untyped)
- Pylint at 10.00/10

## Data Files Required for Integration Tests

- `rail_svc.db` — SQLite database with catalog entities
- `nb/sandbox_catalogs.yaml` — RAIL catalog tag definitions
- HDF5 data files referenced by dataset paths in the DB (at absolute paths on disk)
