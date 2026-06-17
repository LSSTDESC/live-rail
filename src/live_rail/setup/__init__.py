"""Setup profile registry.

Each profile module decorates its class with @register to make it
discoverable via the CLI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from live_rail.setup._base import SetupProfile

PROFILES: dict[str, type[SetupProfile]] = {}


def register(cls: type[SetupProfile]) -> type[SetupProfile]:
    """Class decorator that registers a setup profile."""
    PROFILES[cls.name] = cls
    return cls


def get_profile(name: str) -> type[SetupProfile]:
    """Look up a profile class by name."""
    _ensure_loaded()
    if name not in PROFILES:
        available = ", ".join(PROFILES.keys()) or "(none)"
        raise KeyError(f"Unknown setup profile '{name}'. Available: {available}")
    return PROFILES[name]


def list_profiles() -> list[tuple[str, str]]:
    """Return (name, description) pairs for all registered profiles."""
    _ensure_loaded()
    return [(name, cls.description) for name, cls in PROFILES.items()]


def _ensure_loaded() -> None:
    """Import all profile modules so they self-register."""
    if PROFILES:
        return
    import importlib
    import pkgutil

    import live_rail.setup as pkg

    for info in pkgutil.iter_modules(pkg.__path__):
        if not info.name.startswith("_"):
            importlib.import_module(f"live_rail.setup.{info.name}")
