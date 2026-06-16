"""Tests for BackendProvider singleton, settings, and dispatch."""

import os
from unittest.mock import patch


from live_rail.backend import BackendMode, BackendProvider, BackendSettings


class TestBackendMode:
    def test_local_value(self):
        assert BackendMode.LOCAL == "local"

    def test_remote_value(self):
        assert BackendMode.REMOTE == "remote"


class TestBackendSettings:
    def test_defaults(self):
        s = BackendSettings()
        assert s.mode == BackendMode.LOCAL
        assert "sqlite" in s.db_url
        assert "localhost" in s.server_url
        assert s.auth_token is None
        assert s.catalog_yaml is None

    def test_custom_values(self):
        s = BackendSettings(
            mode=BackendMode.REMOTE,
            db_url="postgres://db",
            server_url="http://remote:9000",
            auth_token="tok123",
            catalog_yaml="/path/to/yaml",
        )
        assert s.mode == BackendMode.REMOTE
        assert s.server_url == "http://remote:9000"
        assert s.auth_token == "tok123"
        assert s.catalog_yaml == "/path/to/yaml"


class TestBackendProviderSingleton:
    def test_get_returns_same_instance(self):
        p1 = BackendProvider.get()
        p2 = BackendProvider.get()
        assert p1 is p2

    def test_reset_clears_instance(self):
        p1 = BackendProvider.get()
        BackendProvider.reset()
        p2 = BackendProvider.get()
        assert p1 is not p2

    def test_default_settings(self):
        provider = BackendProvider.get()
        assert provider.settings.mode == BackendMode.LOCAL


class TestBackendProviderConfigure:
    def test_configure_updates_settings(self, remote_settings):
        provider = BackendProvider.get()
        provider.configure(remote_settings)
        assert provider.settings.mode == BackendMode.REMOTE
        assert provider.settings.server_url == "http://test-server:8000"

    def test_configure_resets_initialized(self, local_settings):
        provider = BackendProvider.get()
        provider._initialized = True
        provider.configure(local_settings)
        assert not provider._initialized


class TestBackendProviderIsLocal:
    def test_local_mode(self, local_settings):
        provider = BackendProvider.get()
        provider.configure(local_settings)
        assert provider.is_local is True

    def test_remote_mode(self, remote_settings):
        provider = BackendProvider.get()
        provider.configure(remote_settings)
        assert provider.is_local is False


class TestBackendProviderInitialize:
    @patch("rail_svc.db.session.init_db")
    def test_local_sets_env_and_calls_init_db(self, mock_init_db, local_settings):
        provider = BackendProvider.get()
        provider.configure(local_settings)
        provider.initialize()

        assert os.environ.get("DB__URL") == local_settings.db_url
        mock_init_db.assert_called_once()
        assert provider._initialized is True

    def test_remote_sets_env_vars(self, remote_settings):
        provider = BackendProvider.get()
        provider.configure(remote_settings)
        provider.initialize()

        assert os.environ.get("PZ_RAIL_SERVICE") == "http://test-server:8000"
        assert os.environ.get("PZ_RAIL_TOKEN") == "test-token"
        assert provider._initialized is True

    @patch("rail_svc.db.session.init_db")
    @patch("rail.utils.catalog_utils.load_yaml")
    def test_catalog_yaml_loaded(self, mock_load_yaml, mock_init_db):
        settings = BackendSettings(
            mode=BackendMode.LOCAL,
            catalog_yaml="/path/catalog.yaml",
        )
        provider = BackendProvider.get()
        provider.configure(settings)
        provider.initialize()

        mock_load_yaml.assert_called_once_with("/path/catalog.yaml")

    @patch("rail_svc.db.session.init_db")
    def test_no_catalog_yaml_skips_load(self, mock_init_db, local_settings):
        provider = BackendProvider.get()
        provider.configure(local_settings)
        with patch("rail.utils.catalog_utils.load_yaml") as mock_load:
            provider.initialize()
            mock_load.assert_not_called()


class TestBackendProviderEntityAccess:
    @patch("rail_svc.db.session.init_db")
    def test_algorithm_local(self, mock_init_db, local_settings):
        provider = BackendProvider.get()
        provider.configure(local_settings)
        provider.initialize()

        # local_sync is a real module — just verify the property returns something
        result = provider.algorithm
        assert result is not None

    def test_algorithm_remote(self, remote_settings):
        provider = BackendProvider.get()
        provider.configure(remote_settings)
        provider.initialize()

        result = provider.algorithm
        assert result is not None

    @patch("rail_svc.db.session.init_db")
    def test_get_ops_by_name(self, mock_init_db, local_settings):
        provider = BackendProvider.get()
        provider.configure(local_settings)
        provider.initialize()

        result = provider.get_ops("dataset")
        assert result is not None

    @patch("rail_svc.db.session.init_db")
    def test_ensure_initialized_calls_init(self, mock_init_db, local_settings):
        provider = BackendProvider.get()
        provider.configure(local_settings)
        assert not provider._initialized

        _ = provider.algorithm

        assert provider._initialized
        mock_init_db.assert_called_once()

    @patch("rail_svc.db.session.init_db")
    def test_is_local_dispatches_correctly(self, mock_init_db, local_settings):
        provider = BackendProvider.get()
        provider.configure(local_settings)
        provider.initialize()
        assert provider.is_local
        # All entity names should be accessible
        for name in ["algorithm", "band", "catalog_tag", "dataset", "estimates", "estimator", "model"]:
            assert provider.get_ops(name) is not None
