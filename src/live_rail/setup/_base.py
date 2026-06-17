"""Base class for setup profiles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from rail_svc import db

from live_rail import rail_svc_utils


class SetupProfile(ABC):
    """Abstract base class for data setup profiles.

    Subclasses implement download() and load() for their specific dataset.
    The run() method orchestrates the full setup sequence.
    """

    name: str
    description: str

    @abstractmethod
    def download(self) -> None:
        """Download required data files."""

    @abstractmethod
    def load(self) -> None:
        """Insert entities into the database."""

    def get_catalog_yaml(self) -> Path | None:
        """Return path to catalog YAML, or None if not applicable."""
        return None

    def get_filter_dir(self) -> Path | None:
        """Return path to filter directory, or None to use default."""
        return None

    def run(self, skip_download: bool = False, catalog_yaml: str | None = None) -> None:
        """Execute the full setup: download, init DB, load catalog, load data."""
        if not skip_download:
            self.download()

        rail_svc_utils.setup_db()
        db.init_db()

        yaml_path = Path(catalog_yaml) if catalog_yaml else self.get_catalog_yaml()
        if yaml_path:
            from rail.utils import path_utils
            from rail_svc import local_sync

            filter_dir = self.get_filter_dir()
            if filter_dir is None:
                filter_dir = Path(path_utils.RAILDIR) / "rail/examples_data/estimation_data/data/FILTER"
            local_sync.funcs.load_catalog_yaml(yaml_path, filter_dir=filter_dir)

        self.load()
