"""Dash application factory."""

from pathlib import Path

from dash import Dash

from .layout import create_layout


def create_app(debug: bool = False) -> Dash:
    """Create the unified multi-page Dash application."""
    pages_dir = Path(__file__).parent / "pages"

    app = Dash(
        __name__,
        use_pages=True,
        pages_folder=str(pages_dir),
        suppress_callback_exceptions=True,
        title="RAIL Dashboard",
    )

    app.layout = create_layout()
    return app
