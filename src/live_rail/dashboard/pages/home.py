"""Home / landing page."""

import dash
from dash import html, callback, Input, Output

from live_rail.backend import BackendProvider

dash.register_page(__name__, path="/", name="Home")


def layout(**kwargs):
    return html.Div(
        [
            html.Div(
                [
                    html.Img(src="/assets/horse.png", style={"height": "400px"}),
                    html.H2("RAIL Dashboard", style={"marginTop": "16px"}),
                ],
                style={"textAlign": "center", "marginBottom": "16px"},
            ),
            html.P("Photometric redshift estimation catalog management and visualization."),
            html.Hr(),
            html.Div(id="home-status"),
        ]
    )


@callback(Output("home-status", "children"), Input("backend-settings", "data"))
def update_status(settings_data):
    provider = BackendProvider.get()
    mode = provider.settings.mode.value
    if provider.settings.mode.value == "local":
        detail = provider.settings.db_url
    else:
        detail = provider.settings.server_url

    try:
        count = provider.algorithm.count_rows()
        connection_status = html.Span(
            f"Connected ({count} algorithms)", style={"color": "green"}
        )
    except Exception as e:
        connection_status = html.Span(f"Error: {e}", style={"color": "red"})

    return html.Div(
        [
            html.H5("Status"),
            html.P([html.Strong("Backend: "), f"{mode} — {detail}"]),
            html.P([html.Strong("Connection: "), connection_status]),
        ]
    )
