"""Shared fixtures for live-rail tests."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from live_rail.backend import BackendMode, BackendProvider, BackendSettings


@pytest.fixture(autouse=True)
def reset_backend():
    """Reset the BackendProvider singleton before each test."""
    BackendProvider.reset()
    yield
    BackendProvider.reset()


@pytest.fixture
def local_settings():
    return BackendSettings(
        mode=BackendMode.LOCAL,
        db_url="sqlite+aiosqlite:///test.db",
        catalog_yaml=None,
    )


@pytest.fixture
def remote_settings():
    return BackendSettings(
        mode=BackendMode.REMOTE,
        server_url="http://test-server:8000",
        auth_token="test-token",
    )


@pytest.fixture
def sample_band():
    """Mock Band model with realistic transmission data."""
    band = MagicMock()
    band.id_ = 1
    band.name = "DC2LSST_g"
    band.band_wavelengths = np.array([400.0, 450.0, 500.0, 550.0, 600.0])
    band.band_transmission = np.array([0.0, 0.3, 0.8, 0.3, 0.0])
    return band


@pytest.fixture
def sample_dataset():
    """Mock Dataset model."""
    ds = MagicMock()
    ds.id_ = 1
    ds.name = "test_dataset"
    ds.path = "/data/test.hdf5"
    ds.n_objects = 100
    ds.is_collection = False
    ds.catalog_tag_id = 1
    return ds


@pytest.fixture
def sample_catalog_tag():
    """Mock CatalogTag model."""
    ct = MagicMock()
    ct.id_ = 1
    ct.name = "rubin"
    return ct


@pytest.fixture
def sample_catalog_band_assocs():
    """Mock list of CatalogBandAssoc models."""
    assocs = []
    for i, (band_id, mag_col, err_col) in enumerate(
        [(1, "mag_g_lsst", "mag_g_lsst_err"), (2, "mag_r_lsst", "mag_r_lsst_err")],
        start=1,
    ):
        a = MagicMock()
        a.id_ = i
        a.band_id = band_id
        a.catalog_tag_id = 1
        a.mag_column_name = mag_col
        a.mag_err_column_name = err_col
        assocs.append(a)
    return assocs


@pytest.fixture
def sample_estimates_list():
    """Mock list of Estimates models."""
    estimates = []
    for i, name in enumerate(["est_knn", "est_bpz"], start=1):
        e = MagicMock()
        e.id_ = i
        e.name = name
        e.path = f"/data/{name}.hdf5"
        e.estimator_id = i
        e.dataset_id = 1
        estimates.append(e)
    return estimates


@pytest.fixture
def dash_app():
    """Create a Dash app for testing page registration and serving."""
    with patch("live_rail.backend.BackendProvider.get") as mock_get:
        provider = MagicMock()
        provider.settings = BackendSettings()
        provider.is_local = True
        mock_get.return_value = provider
        from live_rail.dashboard import create_app

        app = create_app()
        return app
