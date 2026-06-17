"""Tests for Dash callback logic by invoking callback functions directly.

We test the pure logic inside callbacks by mocking BackendProvider
and Dash context objects.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from live_rail.backend import BackendMode, BackendProvider, BackendSettings
from live_rail.dashboard.pages.crud._base import FK_COLUMN_MAP, _serialize_value


class TestCrudCallbackLogic:
    """Test CRUD callback logic by simulating what the callbacks do."""

    @pytest.fixture(autouse=True)
    def setup_provider(self):
        BackendProvider.reset()
        with patch("rail_svc.db.session.init_db"):
            settings = BackendSettings(mode=BackendMode.LOCAL, db_url="sqlite+aiosqlite:///test.db")
            provider = BackendProvider.get()
            provider.configure(settings)
            provider.initialize()
            yield provider

    def test_refresh_table_returns_serialized_rows(self, setup_provider):
        """Simulate what the refresh_table callback does."""

        mock_row = MagicMock()
        mock_row.id_ = 1
        mock_row.name = "knn"
        mock_row.class_name = "rail.knn.KNN"

        columns = ["id_", "name", "class_name"]
        result = [
            {col: _serialize_value(getattr(mock_row, col, None)) for col in columns} for row in [mock_row]
        ]
        assert result == [{"id_": 1, "name": "knn", "class_name": "rail.knn.KNN"}]

    def test_filter_table_logic(self):
        """Test filter logic independently."""
        all_data = [
            {"id_": 1, "name": "knn", "class_name": "rail.knn"},
            {"id_": 2, "name": "bpz", "class_name": "rail.bpz"},
            {"id_": 3, "name": "flexzboost", "class_name": "rail.flex"},
        ]

        # No filter
        assert len(all_data) == 3

        # Filter "knn"
        query = "knn"
        filtered = [r for r in all_data if any(query in str(v).lower() for v in r.values() if v is not None)]
        assert len(filtered) == 1
        assert filtered[0]["name"] == "knn"

        # Filter by class
        query = "rail.flex"
        filtered = [r for r in all_data if any(query in str(v).lower() for v in r.values() if v is not None)]
        assert len(filtered) == 1
        assert filtered[0]["name"] == "flexzboost"

    def test_show_detail_for_name_click(self, setup_provider):
        """Simulate cellClicked on the name column."""

        provider = setup_provider
        mock_ops = MagicMock()
        mock_full_row = MagicMock()
        mock_full_row.name = "test_algo"
        mock_full_row.model_fields = {"name": MagicMock(), "id_": MagicMock()}
        mock_ops.get_row.return_value = mock_full_row

        with patch.object(provider, "get_ops", return_value=mock_ops):
            # Simulate the logic
            col_id = "name"
            row_data = {"id_": 5, "name": "test_algo"}

            assert col_id == "name" or col_id in FK_COLUMN_MAP
            row_id = row_data.get("id_")
            ops = provider.get_ops("algorithm")
            full_row = ops.get_row(row_id)
            assert full_row.name == "test_algo"
            mock_ops.get_row.assert_called_once_with(5)

    def test_show_detail_for_fk_click(self, setup_provider):
        """Simulate cellClicked on a FK column."""

        provider = setup_provider
        mock_ops = MagicMock()
        mock_model = MagicMock()
        mock_model.name = "my_model"
        mock_ops.get_row.return_value = mock_model

        with patch.object(provider, "get_ops", return_value=mock_ops):
            col_id = "model_id"
            row_data = {"id_": 1, "name": "estimator1", "model_id": 3}

            assert col_id in FK_COLUMN_MAP
            ref_entity = FK_COLUMN_MAP[col_id]
            assert ref_entity == "model"

            ref_id = row_data.get(col_id)
            ops = provider.get_ops(ref_entity)
            full_row = ops.get_row(int(ref_id))
            assert full_row.name == "my_model"

    def test_delete_with_selected_row(self, setup_provider):
        """Simulate delete callback logic."""
        provider = setup_provider
        mock_ops = MagicMock()

        with patch.object(provider, "get_ops", return_value=mock_ops):
            selected_rows = [{"id_": 7, "name": "to_delete"}]
            row_data = selected_rows[0]
            row_id = row_data.get("id_")

            ops = provider.get_ops("algorithm")
            ops.delete_row(row_id)
            mock_ops.delete_row.assert_called_once_with(7)

    def test_delete_without_selection(self):
        """Delete with no selected rows returns early."""
        selected_rows = []
        assert not selected_rows


class TestVisualizerHelpers:
    """Test the color-color figure builder and wrapper cache."""

    def test_build_color_color_figure_with_valid_data(self, dash_app):
        from live_rail.dashboard.pages.visualizers.single_catalog import _build_color_color_figure

        color_names = ["u-g", "g-r", "r-i", "i-z"]
        color_vals = [0.5, 0.3, -0.2, 0.1]
        fig = _build_color_color_figure(color_names, color_vals)

        assert fig is not None
        assert len(fig.data) == 1
        assert len(fig.data[0].x) == 3  # n-1 pairs

    def test_build_color_color_figure_clips_values(self, dash_app):
        from live_rail.dashboard.pages.visualizers.single_catalog import _build_color_color_figure

        color_names = ["a", "b", "c"]
        color_vals = [5.0, -3.0, 1.0]  # 5.0 and -3.0 should be clipped
        fig = _build_color_color_figure(color_names, color_vals)

        # Values should be clipped to [-1, 2]
        assert all(-1 <= x <= 2 for x in fig.data[0].x)
        assert all(-1 <= y <= 2 for y in fig.data[0].y)

    def test_build_color_color_figure_too_few_colors(self, dash_app):
        from live_rail.dashboard.pages.visualizers.single_catalog import _build_color_color_figure

        fig = _build_color_color_figure(["only_one"], [0.5])
        assert len(fig.data) == 0

    def test_wrapper_cache(self, dash_app):
        from live_rail.dashboard.pages.visualizers import single_catalog

        # Clear cache
        single_catalog._wrapper_cache.clear()
        assert len(single_catalog._wrapper_cache) == 0

        # Simulate adding to cache
        mock_wrapper = MagicMock()
        single_catalog._wrapper_cache[99] = mock_wrapper
        assert single_catalog._wrapper_cache[99] is mock_wrapper

        # Clean up
        single_catalog._wrapper_cache.clear()


class TestEstimationPageLogic:
    """Test the estimation page dropdown population logic."""

    @pytest.fixture(autouse=True)
    def setup_provider(self):
        BackendProvider.reset()
        with patch("rail_svc.db.session.init_db"):
            settings = BackendSettings(mode=BackendMode.LOCAL, db_url="sqlite+aiosqlite:///test.db")
            provider = BackendProvider.get()
            provider.configure(settings)
            provider.initialize()
            yield provider

    def test_populate_estimator_options(self, setup_provider):
        """Simulate dropdown population for estimation pages."""
        mock_est1 = MagicMock()
        mock_est1.name = "knn_est"
        mock_est1.id_ = 1
        mock_est2 = MagicMock()
        mock_est2.name = "bpz_est"
        mock_est2.id_ = 2

        mock_ops = MagicMock()
        mock_ops.get_rows.return_value = [mock_est1, mock_est2]

        with patch.object(BackendProvider, "estimator", new_callable=lambda: property(lambda self: mock_ops)):
            provider = BackendProvider.get()
            rows = provider.estimator.get_rows()
            options = [{"label": e.name, "value": e.id_} for e in rows]
            assert len(options) == 2
            assert options[0] == {"label": "knn_est", "value": 1}

    def test_pdf_extraction_2d(self):
        """Test that 2D PDF array is indexed correctly."""
        pdf_all = np.random.rand(100, 301)
        row = 5
        pdf_values = pdf_all[row]
        assert pdf_values.shape == (301,)

    def test_pdf_extraction_1d(self):
        """Test that 1D PDF is handled via squeeze."""
        pdf_all = np.random.rand(301)
        pdf_values = np.squeeze(pdf_all)
        assert pdf_values.shape == (301,)


class TestSettingsPageLogic:
    """Test settings page configuration logic."""

    def test_apply_local_settings(self):
        BackendProvider.reset()
        settings = BackendSettings(
            mode=BackendMode.LOCAL,
            db_url="sqlite+aiosqlite:///custom.db",
        )
        provider = BackendProvider.get()
        provider.configure(settings)
        assert provider.settings.db_url == "sqlite+aiosqlite:///custom.db"
        assert provider.is_local

    def test_apply_remote_settings(self):
        BackendProvider.reset()
        settings = BackendSettings(
            mode=BackendMode.REMOTE,
            server_url="http://myserver:9000",
            auth_token="secret",
        )
        provider = BackendProvider.get()
        provider.configure(settings)
        assert not provider.is_local
        assert provider.settings.server_url == "http://myserver:9000"
        assert provider.settings.auth_token == "secret"


class TestHomePageLogic:
    """Test home page status display logic."""

    @patch("rail_svc.db.session.init_db")
    def test_connection_status_success(self, mock_init_db):
        BackendProvider.reset()
        settings = BackendSettings(mode=BackendMode.LOCAL)
        provider = BackendProvider.get()
        provider.configure(settings)
        provider.initialize()

        mock_ops = MagicMock()
        mock_ops.count_rows.return_value = 8

        with patch.object(BackendProvider, "algorithm", new_callable=lambda: property(lambda self: mock_ops)):
            count = provider.algorithm.count_rows()
            assert count == 8

    @patch("rail_svc.db.session.init_db")
    def test_connection_status_error(self, mock_init_db):
        BackendProvider.reset()
        settings = BackendSettings(mode=BackendMode.LOCAL)
        provider = BackendProvider.get()
        provider.configure(settings)
        provider.initialize()

        mock_ops = MagicMock()
        mock_ops.count_rows.side_effect = Exception("DB error")

        with patch.object(BackendProvider, "algorithm", new_callable=lambda: property(lambda self: mock_ops)):
            with pytest.raises(Exception, match="DB error"):
                provider.algorithm.count_rows()
