"""Integration tests that exercise the full stack against the real SQLite database.

Run with: pytest tests/test_integration.py -m integration -v
These are excluded from default test runs (require real DB + data files).
"""

from pathlib import Path

import dash
import numpy as np
import pytest
import qp

from live_rail.backend import BackendMode, BackendProvider, BackendSettings
from live_rail.dashboard import create_app
from live_rail.dashboard.pages.crud._base import _serialize_value
from live_rail.wrappers.rail_svc_wrapper import RailSvcLocalCatalogWrapper

DB_PATH = Path(__file__).parent.parent / "rail_svc.db"
CATALOG_YAML = Path(__file__).parent.parent / "nb" / "sandbox_catalogs.yaml"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def provider():
    """Initialize the backend provider with the real database."""
    if not DB_PATH.exists():
        pytest.skip(f"Database not found: {DB_PATH}")
    if not CATALOG_YAML.exists():
        pytest.skip(f"Catalog YAML not found: {CATALOG_YAML}")

    BackendProvider.reset()
    settings = BackendSettings(
        mode=BackendMode.LOCAL,
        db_url=f"sqlite+aiosqlite:///{DB_PATH}",
        catalog_yaml=str(CATALOG_YAML),
    )
    p = BackendProvider.get()
    p.configure(settings)
    p.initialize()
    yield p
    BackendProvider.reset()


# --- Backend + Real DB ---


class TestBackendWithRealDB:
    def test_algorithm_get_rows(self, provider):
        algos = provider.algorithm.get_rows()
        assert len(algos) == 8
        names = [a.name for a in algos]
        assert "knn" in names
        assert "bpz" in names

    def test_dataset_get_row(self, provider):
        ds = provider.dataset.get_row(1)
        assert ds.n_objects == 40000
        assert ds.name is not None

    def test_estimator_get_rows(self, provider):
        estimators = provider.estimator.get_rows()
        assert len(estimators) == 24

    def test_dataset_assoc_find_by(self, provider):
        assocs = provider.dataset_assoc.find_by(matched_dataset_id=3)
        assert len(assocs) >= 2
        for a in assocs:
            assert a.matched_dataset_id == 3

    def test_get_dataset_and_estimates(self, provider):
        result = provider.funcs.get_dataset_and_estimates(1)
        dataset, estimates_list = result
        assert dataset.id_ == 1
        assert len(estimates_list) >= 1


# --- Wrappers + Real Data ---


class TestWrappersWithRealData:
    @pytest.fixture
    def wrapper(self, provider):
        return RailSvcLocalCatalogWrapper(1)

    def test_wrapper_init(self, wrapper):
        assert wrapper.get_nobjects() == 40000
        assert len(wrapper.get_band_names()) >= 3

    def test_get_object_magnitudes(self, wrapper):
        obj = wrapper.get_object(0)
        mags = obj.get_magnitudes()
        assert isinstance(mags, np.ndarray)
        assert mags.ndim == 1
        assert len(mags) == len(wrapper.get_band_names())

    def test_get_object_colors_are_scalars(self, wrapper):
        obj = wrapper.get_object(0)
        colors = obj.get_colors()
        assert len(colors) >= 2
        for name, (val, err) in colors.items():
            assert isinstance(float(val), float)
            assert isinstance(float(err), float)

    def test_get_object_redshift_estimates(self, wrapper):
        obj = wrapper.get_object(0)
        estimates = obj.get_redshift_estimates()
        assert len(estimates) >= 1
        for name, ens in estimates.items():
            assert isinstance(ens, qp.Ensemble)


# --- Dash App + Real Data ---


class TestDashAppWithRealData:
    @pytest.fixture(scope="class")
    def app(self, provider):
        return create_app()

    def test_all_pages_serve_200(self, app):
        with app.server.test_client() as client:
            for page in dash.page_registry.values():
                resp = client.get(page["path"])
                assert resp.status_code == 200, f"{page['path']} returned {resp.status_code}"

    def test_crud_refresh_returns_data(self, provider):

        ops = provider.get_ops("algorithm")
        rows = ops.get_rows()
        table_data = [
            {col: _serialize_value(getattr(row, col, None)) for col in ["id_", "name", "class_name"]}
            for row in rows
        ]
        assert len(table_data) == 8
        assert all("name" in row for row in table_data)
        assert all(isinstance(row["id_"], int) for row in table_data)

    def test_color_color_figure_with_real_data(self, app, provider):
        from live_rail.dashboard.pages.visualizers.single_catalog import _build_color_color_figure

        wrapper = RailSvcLocalCatalogWrapper(1)
        obj = wrapper.get_object(5)
        colors = obj.get_colors()
        color_names = list(colors.keys())
        color_vals = [colors[c][0] for c in color_names]

        fig = _build_color_color_figure(color_names, color_vals)
        assert len(fig.data) == 1
        assert len(fig.data[0].x) == len(color_names) - 1

    def test_estimate_pdf_returns_correct_shape(self, provider):
        result = provider.funcs.estimate_pdf(estimator_id=1, dataset_id=1, row=0)
        zgrid = np.linspace(0, 3, 301)
        pdf_all = result.pdf(zgrid)
        # May be 2D (all objects) or 1D (single object)
        if pdf_all.ndim == 2:
            pdf_values = pdf_all[0]
        else:
            pdf_values = np.squeeze(pdf_all)
        assert pdf_values.shape == (301,)
        assert pdf_values.max() > 0
