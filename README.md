# live-rail

Unified dashboard for RAIL photometric redshift estimation catalog management and visualization.

## Overview

`live-rail` provides a multi-page Dash web application for:

- **CRUD management** of photo-z catalog entities (algorithms, bands, catalog tags, datasets, models, estimators, estimates)
- **Estimation workflows** — run photo-z PDF estimation, ensemble estimation, and full dataset estimation
- **Interactive visualization** — single-catalog and multi-catalog photometric spectrum, color-color diagrams, and redshift PDF comparison

All backed by the `pz-rail-svc` package, supporting both local SQLite database access and remote FastAPI server access.

## Installation

```bash
pip install -e '.[dev]'
```

## Quick Start

```bash

# Download data set set up local SQLite DB
python scripts/setup_pzdc.py

# Launch the dashboard (uses local SQLite DB)
live-rail dashboard --backend local --db-url "sqlite+aiosqlite:///rail_svc.db"

# With RAIL catalog config for live estimators
live-rail dashboard --catalog-yaml nb/sandbox_catalogs.yaml

# Connect to a remote rail_svc server
live-rail dashboard --backend remote --server-url http://localhost:8000
```

Then open http://127.0.0.1:8050 in your browser.

## Features

### CRUD Tables
- AG Grid tables with sorting, filtering, and pagination
- Click entity names to see full details in a popup
- Click FK columns (model_id, dataset_id, etc.) to see the referenced entity
- Create and delete entities via modal forms

### Visualizers
- **Single Catalog**: Photometric spectrum, color-color diagram (all adjacent pairs), and redshift PDF estimates for any object in a dataset
- **Multi Catalog**: Same layout comparing across component catalogs in a matched (collection) dataset
- Navigate objects with slider or back/next buttons
- Pre-computed and live estimator PDFs with true redshift overlay

### Estimation
- Run photo-z PDF estimation for a single object
- Run ensemble estimation for an entire catalog
- Run full dataset estimation (creates estimates record in DB)

## Development

```bash
# Run unit tests
pytest

# Run integration tests (requires real DB + data files)
pytest -m integration

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/

# Pylint
pylint src/live_rail/ --rcfile=pyproject.toml
```

## Project Structure

```
src/live_rail/
├── backend/          # BackendProvider — switches between local/remote rail_svc
├── cli/              # Click CLI (live-rail dashboard)
├── dashboard/        # Dash multi-page app
│   ├── pages/crud/   # CRUD pages for each entity
│   ├── pages/estimation/  # Estimation workflow pages
│   └── pages/visualizers/ # Interactive visualizer pages
└── wrappers/         # CatalogWrapper abstractions for data access
```

## License

MIT
