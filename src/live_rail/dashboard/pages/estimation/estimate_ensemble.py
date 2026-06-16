"""Estimate Ensemble page: run ensemble estimation to output file."""

import dash
from dash import Input, Output, State, callback, dcc, html

from live_rail.backend import BackendProvider

dash.register_page(__name__, path="/estimation/ensemble", name="Estimate Ensemble")


def layout(**kwargs):
    return html.Div(
        [
            html.H2("Estimate Ensemble"),
            html.P("Run ensemble estimation for a dataset and save results to file."),
            html.Hr(),
            html.Div(
                [
                    html.Label("Estimator"),
                    dcc.Dropdown(id="est-ens-estimator", placeholder="Select estimator..."),
                    html.Label("Dataset", style={"marginTop": "12px"}),
                    dcc.Dropdown(id="est-ens-dataset", placeholder="Select dataset..."),
                    html.Label("Output File Path", style={"marginTop": "12px"}),
                    dcc.Input(
                        id="est-ens-output-path",
                        type="text",
                        placeholder="/path/to/output.hdf5",
                        style={"width": "100%"},
                    ),
                    html.Button(
                        "Run Ensemble",
                        id="est-ens-run-btn",
                        n_clicks=0,
                        style={"marginTop": "16px", "padding": "8px 24px"},
                    ),
                    html.Div(id="est-ens-status", style={"marginTop": "12px"}),
                ],
                style={"maxWidth": "400px"},
            ),
        ]
    )


@callback(
    Output("est-ens-estimator", "options"),
    Output("est-ens-dataset", "options"),
    Input("est-ens-estimator", "id"),
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
    Output("est-ens-status", "children"),
    Input("est-ens-run-btn", "n_clicks"),
    State("est-ens-estimator", "value"),
    State("est-ens-dataset", "value"),
    State("est-ens-output-path", "value"),
    prevent_initial_call=True,
)
def run_ensemble(n_clicks, estimator_id, dataset_id, output_path):
    if not estimator_id or not dataset_id or not output_path:
        return html.Span("All fields required.", style={"color": "orange"})

    provider = BackendProvider.get()
    try:
        funcs = provider.funcs
        result = funcs.estimate_ensemble(
            estimator_id=estimator_id,
            dataset_id=dataset_id,
            output_file_path=output_path,
        )
        return html.Span(f"Written to: {result}", style={"color": "green"})
    except Exception as e:
        return html.Span(f"Error: {e}", style={"color": "red"})
