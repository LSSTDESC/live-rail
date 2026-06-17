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
# Set up test data (downloads data + initializes local SQLite DB)
live-rail setup pzdc

# Or skip the download if data is already present
live-rail setup pzdc --skip-download

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
- Multi-row selection with select-all checkbox (Bands, Catalog Tags)
- Click entity names to see full details in a popup
- Click FK columns (model_id, dataset_id, etc.) to see the referenced entity
- Create and delete entities via modal forms
- Band transmission curve visualization for selected bands/catalog tags

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

## Data Setup

The `live-rail setup` command manages data initialization. Setup profiles are extensible — each profile handles downloading data and populating the database.

```bash
# List available setup profiles
live-rail setup --list-profiles dummy

# Run a profile
live-rail setup pzdc

# Skip download (data already on disk)
live-rail setup pzdc --skip-download

# Override catalog YAML
live-rail setup pzdc --catalog-yaml path/to/catalogs.yaml
```

Available profiles:
- **pzdc** — Photo-z Data Challenge sandbox data (roman + rubin, 1yr + 10yr)

To add a new profile, create a module in `src/live_rail/setup/` that subclasses `SetupProfile` and decorates with `@register`.

## Project Structure

```
src/live_rail/
├── backend/          # BackendProvider — switches between local/remote rail_svc
├── cli/              # Click CLI (live-rail dashboard, live-rail setup)
├── dashboard/        # Dash multi-page app
│   ├── pages/crud/   # CRUD pages for each entity
│   ├── pages/estimation/  # Estimation workflow pages
│   └── pages/visualizers/ # Interactive visualizer pages
├── setup/            # Extensible data setup profiles
└── wrappers/         # CatalogWrapper abstractions for data access
```

## License

MIT
