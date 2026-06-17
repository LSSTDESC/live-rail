"""Settings page for backend configuration."""

import dash
from dash import Input, Output, State, callback, dcc, html

from live_rail.backend import BackendMode, BackendProvider, BackendSettings

dash.register_page(__name__, path="/settings", name="Settings")


def layout(**kwargs):
    provider = BackendProvider.get()
    s = provider.settings

    return html.Div(
        [
            html.H2("Settings"),
            html.P("Configure the backend connection for the dashboard."),
            html.Hr(),
            html.Div(
                [
                    html.Label("Backend Mode"),
                    dcc.RadioItems(
                        id="settings-mode",
                        options=[
                            {"label": "Local Database", "value": "local"},
                            {"label": "Remote Server", "value": "remote"},
                        ],
                        value=s.mode.value,
                        style={"marginBottom": "16px"},
                    ),
                    html.Div(
                        [
                            html.Label("Database URL"),
                            dcc.Input(
                                id="settings-db-url",
                                type="text",
                                value=s.db_url,
                                style={"width": "100%", "marginBottom": "12px"},
                            ),
                        ],
                        id="settings-local-section",
                    ),
                    html.Div(
                        [
                            html.Label("Server URL"),
                            dcc.Input(
                                id="settings-server-url",
                                type="text",
                                value=s.server_url,
                                style={"width": "100%", "marginBottom": "12px"},
                            ),
                            html.Label("Auth Token (optional)"),
                            dcc.Input(
                                id="settings-token",
                                type="password",
                                value=s.auth_token or "",
                                style={"width": "100%", "marginBottom": "12px"},
                            ),
                        ],
                        id="settings-remote-section",
                    ),
                    html.Button(
                        "Apply",
                        id="settings-apply-btn",
                        n_clicks=0,
                        style={"marginTop": "16px", "padding": "8px 24px"},
                    ),
                    html.Div(id="settings-status", style={"marginTop": "12px"}),
                ],
                style={"maxWidth": "500px"},
            ),
        ]
    )


@callback(
    Output("settings-local-section", "style"),
    Output("settings-remote-section", "style"),
    Input("settings-mode", "value"),
)
def toggle_sections(mode):
    if mode == "local":
        return {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "block"}


@callback(
    Output("backend-settings", "data"),
    Output("settings-status", "children"),
    Input("settings-apply-btn", "n_clicks"),
    State("settings-mode", "value"),
    State("settings-db-url", "value"),
    State("settings-server-url", "value"),
    State("settings-token", "value"),
    prevent_initial_call=True,
)
def apply_settings(n_clicks, mode, db_url, server_url, token):
    settings = BackendSettings(
        mode=BackendMode(mode),
        db_url=db_url or "sqlite+aiosqlite:///rail_svc.db",
        server_url=server_url or "http://localhost:8000",
        auth_token=token or None,
    )

    provider = BackendProvider.get()
    provider.configure(settings)
    try:
        provider.initialize()
        status = html.Span("Applied successfully.", style={"color": "green"})
    except Exception as e:
        status = html.Span(f"Error: {e}", style={"color": "red"})

    store_data = {
        "mode": settings.mode.value,
        "db_url": settings.db_url,
        "server_url": settings.server_url,
        "auth_token": settings.auth_token,
    }
    return store_data, status
