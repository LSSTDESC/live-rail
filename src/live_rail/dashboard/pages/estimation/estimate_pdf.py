"""Estimate PDF page: run a single photo-z PDF estimation."""

import dash
import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html, no_update

from live_rail.backend import BackendProvider

dash.register_page(__name__, path="/estimation/pdf", name="Estimate PDF")


def layout(**kwargs):
    return html.Div(
        [
            html.H2("Estimate PDF"),
            html.P("Run a photo-z PDF estimation for a single object in a dataset."),
            html.Hr(),
            html.Div(
                [
                    html.Label("Estimator"),
                    dcc.Dropdown(id="est-pdf-estimator", placeholder="Select estimator..."),
                    html.Label("Dataset", style={"marginTop": "12px"}),
                    dcc.Dropdown(id="est-pdf-dataset", placeholder="Select dataset..."),
                    html.Label("Row Index", style={"marginTop": "12px"}),
                    dcc.Input(id="est-pdf-row", type="number", value=0, min=0),
                    html.Button(
                        "Run Estimate",
                        id="est-pdf-run-btn",
                        n_clicks=0,
                        style={"marginTop": "16px", "padding": "8px 24px"},
                    ),
                    html.Div(id="est-pdf-status", style={"marginTop": "8px"}),
                ],
                style={"maxWidth": "400px", "marginBottom": "24px"},
            ),
            dcc.Graph(id="est-pdf-plot", style={"display": "none"}),
        ]
    )


@callback(
    Output("est-pdf-estimator", "options"),
    Output("est-pdf-dataset", "options"),
    Input("est-pdf-estimator", "id"),
)
def populate_dropdowns(_):
    provider = BackendProvider.get()
    try:
        estimators = provider.estimator.get_rows()
        datasets = provider.dataset.get_rows()
        est_options = [{"label": e.name, "value": e.id_} for e in estimators]
        ds_options = [{"label": d.name, "value": d.id_} for d in datasets]
        return est_options, ds_options
    except Exception:
        return [], []


@callback(
    Output("est-pdf-plot", "figure"),
    Output("est-pdf-plot", "style"),
    Output("est-pdf-status", "children"),
    Input("est-pdf-run-btn", "n_clicks"),
    State("est-pdf-estimator", "value"),
    State("est-pdf-dataset", "value"),
    State("est-pdf-row", "value"),
    prevent_initial_call=True,
)
def run_estimate(n_clicks, estimator_id, dataset_id, row):
    if not estimator_id or not dataset_id:
        return no_update, no_update, html.Span("Select estimator and dataset.", style={"color": "orange"})

    row = int(row or 0)
    provider = BackendProvider.get()
    try:
        funcs = provider.funcs
        result = funcs.estimate_pdf(
            estimator_id=estimator_id,
            dataset_id=dataset_id,
            row=row,
        )

        zgrid = np.linspace(0, 3, 301)
        pdf_all = result.pdf(zgrid)
        # Result may contain all objects — extract the specific row
        if pdf_all.ndim == 2:
            pdf_values = pdf_all[row]
        else:
            pdf_values = np.squeeze(pdf_all)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=zgrid.tolist(),
                y=pdf_values.tolist(),
                mode="lines",
                name="p(z)",
            )
        )
        fig.update_layout(
            xaxis_title="Redshift",
            yaxis_title="p(z)",
            template="plotly_white",
            margin=dict(t=30, b=40, l=50, r=10),
        )

        return fig, {"display": "block"}, html.Span(f"Success (row {row})", style={"color": "green"})
    except Exception as e:
        return no_update, no_update, html.Span(f"Error: {e}", style={"color": "red"})
