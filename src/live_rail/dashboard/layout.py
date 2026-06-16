"""Top-level app layout with sidebar navigation and page container."""

from dash import Input, Output, callback, dcc, html, page_container

from .nav import create_sidebar


@callback(
    Output("header-logo", "style"),
    Input("url", "pathname"),
)
def toggle_logo(pathname):
    base = {"height": "100px", "position": "fixed", "top": "8px", "right": "16px"}
    if pathname == "/":
        return {**base, "display": "none"}
    return base


def create_layout() -> html.Div:
    """Create the top-level layout with sidebar + page content."""
    return html.Div(
        [
            dcc.Store(id="backend-settings", storage_type="local"),
            dcc.Location(id="url", refresh=False),
            html.Div(
                [
                    create_sidebar(),
                    html.Div(
                        [
                            # Page content with logo floating right
                            html.Div(
                                [
                                    html.Div(
                                        page_container,
                                        style={"flex": "1"},
                                    ),
                                    html.Img(
                                        id="header-logo",
                                        src="/assets/horse.png",
                                        style={
                                            "height": "100px",
                                            "position": "fixed",
                                            "top": "8px",
                                            "right": "16px",
                                        },
                                    ),
                                ],
                                style={"padding": "20px", "flex": "1", "overflow": "auto"},
                            ),
                        ],
                        id="page-content",
                        style={"flex": "1", "display": "flex", "flexDirection": "column", "height": "100vh"},
                    ),
                ],
                style={"display": "flex", "height": "100vh"},
            ),
        ]
    )
