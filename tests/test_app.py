"""Tests for the Dash app factory and page registration."""

from unittest.mock import MagicMock, patch

import dash

from live_rail.dashboard import create_app


class TestCreateApp:
    @patch("live_rail.backend.BackendProvider.get")
    def test_returns_dash_instance(self, mock_get):
        mock_get.return_value = MagicMock()
        app = create_app()
        assert isinstance(app, dash.Dash)

    @patch("live_rail.backend.BackendProvider.get")
    def test_registers_all_pages(self, mock_get):
        mock_get.return_value = MagicMock()
        _app = create_app()
        pages = list(dash.page_registry.keys())
        assert len(pages) == 16

    @patch("live_rail.backend.BackendProvider.get")
    def test_expected_paths_registered(self, mock_get):
        mock_get.return_value = MagicMock()
        _app = create_app()
        paths = [p["path"] for p in dash.page_registry.values()]
        assert "/" in paths
        assert "/settings" in paths
        assert "/crud/algorithm" in paths
        assert "/crud/dataset" in paths
        assert "/estimation/pdf" in paths
        assert "/visualize/single" in paths
        assert "/visualize/multi" in paths

    @patch("live_rail.backend.BackendProvider.get")
    def test_pages_serve_200(self, mock_get):
        mock_get.return_value = MagicMock()
        app = create_app()
        with app.server.test_client() as client:
            for path in ["/", "/settings", "/crud/algorithm"]:
                resp = client.get(path)
                assert resp.status_code == 200, f"{path} returned {resp.status_code}"

    @patch("live_rail.backend.BackendProvider.get")
    def test_logo_asset_served(self, mock_get):
        mock_get.return_value = MagicMock()
        app = create_app()
        with app.server.test_client() as client:
            resp = client.get("/assets/horse.png")
            assert resp.status_code == 200
