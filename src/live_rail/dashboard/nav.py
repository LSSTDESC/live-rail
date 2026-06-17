"""Sidebar navigation component."""

from dash import dcc, html

SIDEBAR_STYLE = {
    "width": "220px",
    "backgroundColor": "#f8f9fa",
    "padding": "20px 10px",
    "borderRight": "1px solid #dee2e6",
    "overflowY": "auto",
    "height": "100vh",
}

LINK_STYLE = {
    "display": "block",
    "padding": "6px 12px",
    "textDecoration": "none",
    "color": "#333",
    "borderRadius": "4px",
    "marginBottom": "2px",
}

SECTION_STYLE = {
    "fontSize": "11px",
    "fontWeight": "bold",
    "textTransform": "uppercase",
    "color": "#888",
    "padding": "12px 12px 4px",
    "letterSpacing": "0.5px",
}


def _nav_link(label: str, href: str) -> dcc.Link:
    return dcc.Link(label, href=href, style=LINK_STYLE)


def _section_header(label: str) -> html.Div:
    return html.Div(label, style=SECTION_STYLE)


def create_sidebar() -> html.Div:
    """Create the sidebar navigation."""
    return html.Div(
        [
            html.H4("RAIL", style={"padding": "0 12px", "marginBottom": "20px"}),
            _nav_link("Home", "/"),
            _nav_link("Settings", "/settings"),
            _section_header("Catalog"),
            _nav_link("Algorithms", "/crud/algorithm"),
            _nav_link("Bands", "/crud/band"),
            _nav_link("Catalog Tags", "/crud/catalog-tag"),
            _nav_link("Band Associations", "/crud/catalog-band-assoc"),
            _section_header("Data"),
            _nav_link("Datasets", "/crud/dataset"),
            _nav_link("Dataset Associations", "/crud/dataset-assoc"),
            _nav_link("Models", "/crud/model"),
            _nav_link("Estimators", "/crud/estimator"),
            _nav_link("Estimates", "/crud/estimates"),
            _section_header("Estimation"),
            _nav_link("Estimate PDF", "/estimation/pdf"),
            _nav_link("Estimate Ensemble", "/estimation/ensemble"),
            _nav_link("Estimate Dataset", "/estimation/dataset"),
            _section_header("Visualize"),
            _nav_link("Single Catalog", "/visualize/single"),
            _nav_link("Multi Catalog", "/visualize/multi"),
        ],
        style=SIDEBAR_STYLE,
    )
