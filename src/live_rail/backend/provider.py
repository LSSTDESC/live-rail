"""Backend provider that abstracts local vs remote rail_svc access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any


class BackendMode(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


@dataclass
class BackendSettings:
    mode: BackendMode = BackendMode.LOCAL
    db_url: str = "sqlite+aiosqlite:///rail_svc.db"
    server_url: str = "http://localhost:8000"
    auth_token: str | None = None
    catalog_yaml: str | None = None


class BackendProvider:
    """Singleton providing the correct rail_svc operations based on settings."""

    _instance: BackendProvider | None = None

    def __init__(self) -> None:
        self._settings = BackendSettings()
        self._initialized = False

    @classmethod
    def get(cls) -> BackendProvider:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @property
    def settings(self) -> BackendSettings:
        return self._settings

    @property
    def is_local(self) -> bool:
        return self._settings.mode == BackendMode.LOCAL

    def configure(self, settings: BackendSettings) -> None:
        self._settings = settings
        self._initialized = False

    def initialize(self) -> None:
        if self._settings.mode == BackendMode.LOCAL:
            os.environ["DB__URL"] = self._settings.db_url
            from rail_svc.db.session import init_db
            init_db()
        else:
            os.environ["PZ_RAIL_SERVICE"] = self._settings.server_url
            if self._settings.auth_token:
                os.environ["PZ_RAIL_TOKEN"] = self._settings.auth_token

        if self._settings.catalog_yaml:
            from rail.utils import catalog_utils
            catalog_utils.load_yaml(self._settings.catalog_yaml)

        self._initialized = True

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    @property
    def algorithm(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.algorithm
        from rail_svc import remote_sync
        return remote_sync.algorithm()

    @property
    def band(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.band
        from rail_svc import remote_sync
        return remote_sync.band()

    @property
    def catalog_tag(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.catalog_tag
        from rail_svc import remote_sync
        return remote_sync.catalog_tag()

    @property
    def catalog_band_assoc(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.catalog_band_assoc
        from rail_svc import remote_sync
        return remote_sync.catalog_band_assoc()

    @property
    def dataset(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.dataset
        from rail_svc import remote_sync
        return remote_sync.dataset()

    @property
    def dataset_assoc(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.dataset_assoc
        from rail_svc import remote_sync
        return remote_sync.dataset_assoc()

    @property
    def estimates(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.estimates
        from rail_svc import remote_sync
        return remote_sync.estimates()

    @property
    def estimator(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.estimator
        from rail_svc import remote_sync
        return remote_sync.estimator()

    @property
    def model(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.model
        from rail_svc import remote_sync
        return remote_sync.model()

    @property
    def funcs(self) -> Any:
        self._ensure_initialized()
        if self.is_local:
            from rail_svc import local_sync
            return local_sync.funcs
        from rail_svc import remote_sync
        return remote_sync.funcs()

    def get_ops(self, entity_name: str) -> Any:
        """Get operations object by entity name string."""
        return getattr(self, entity_name)
