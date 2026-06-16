"""Estimate Dataset page: run full dataset estimation."""

import dash
from dash import Input, Output, State, callback, dcc, html, no_update

from live_rail.backend import BackendProvider

dash.register_page(__name__, path="/estimation/dataset", name="Estimate Dataset")


def layout(**kwargs):
    return html.Div(
        [
            html.H2("Estimate Dataset"),
            html.P("Run photo-z estimation for an entire dataset with a given estimator."),
            html.Hr(),
            html.Div(
                [
                    html.Label("Estimator"),
                    dcc.Dropdown(id="est-ds-estimator", placeholder="Select estimator..."),
                    html.Label("Dataset", style={"marginTop": "12px"}),
                    dcc.Dropdown(id="est-ds-dataset", placeholder="Select dataset..."),
                    html.Button(
                        "Run Dataset Estimation",
                        id="est-ds-run-btn",
                        n_clicks=0,
                        style={"marginTop": "16px", "padding": "8px 24px"},
                    ),
                    html.Div(id="est-ds-status", style={"marginTop": "12px"}),
                ],
                style={"maxWidth": "400px"},
            ),
            html.Div(id="est-ds-result", style={"marginTop": "24px"}),
        ]
    )


@callback(
    Output("est-ds-estimator", "options"),
    Output("est-ds-dataset", "options"),
    Input("est-ds-estimator", "id"),
)
def populate_dropdowns(_):
    provider = BackendProvider.get()
    try:
        estimators = provider.estimator.get_rows()
        datasets = provider.dataset.get_rows()
        return (
            [{"label": e.name, "value": e.id_} for e in estimators],
            [{"label": d.name, "value": d.id_} for d in datasets],
        )
    except Exception:
        return [], []


@callback(
    Output("est-ds-status", "children"),
    Output("est-ds-result", "children"),
    Input("est-ds-run-btn", "n_clicks"),
    State("est-ds-estimator", "value"),
    State("est-ds-dataset", "value"),
    prevent_initial_call=True,
)
def run_estimate_dataset(n_clicks, estimator_id, dataset_id):
    if not estimator_id or not dataset_id:
        return html.Span("Select estimator and dataset.", style={"color": "orange"}), no_update

    provider = BackendProvider.get()
    try:
        funcs = provider.funcs
        result = funcs.estimate_dataset(
            estimator_id=estimator_id,
            dataset_id=dataset_id,
        )

        # result is an Estimates pydantic model (local) or dict (remote)
        if hasattr(result, "name"):
            detail = html.Div(
                [
                    html.H5("Result"),
                    html.P(f"Estimates name: {result.name}"),
                    html.P(f"Path: {result.path}"),
                    html.P(f"ID: {result.id_}"),
                ]
            )
        else:
            detail = html.Pre(str(result))

        return html.Span("Estimation complete.", style={"color": "green"}), detail
    except Exception as e:
        return html.Span(f"Error: {e}", style={"color": "red"}), no_update
