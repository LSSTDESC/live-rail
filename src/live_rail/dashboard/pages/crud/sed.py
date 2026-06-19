"""CRUD page for Sed with multi-select and SED curve visualization."""

import dash
import plotly.graph_objs as go
from dash import Input, Output, callback, dcc, html
from rail_svc import models

from live_rail.backend import BackendProvider
from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="sed",
    display_name="SEDs",
    response_model=models.Sed,
    create_model=models.SedCreate,
    table_columns=["id_", "name"],
    multi_select=True,
    extra_layout=[
        html.Div(
            [
                html.H4("SED Curves", style={"marginTop": "16px"}),
                dcc.Graph(
                    id="sed-curve-plot",
                    config={"responsive": True},
                    style={"height": "350px"},
                    figure=go.Figure().update_layout(
                        xaxis_title="Wavelength (nm)",
                        yaxis_title="SED Value",
                        template="plotly_white",
                        margin=dict(t=10, b=40, l=50, r=10),
                    ),
                ),
            ],
        ),
    ],
)

dash.register_page(__name__, path="/crud/sed", name="SEDs")
layout = make_crud_layout(config)
register_crud_callbacks(config)


@callback(
    Output("sed-curve-plot", "figure"),
    Input("sed-table", "selectedRows"),
)
def update_sed_plot(selected_rows):
    fig = go.Figure()

    if selected_rows:
        provider = BackendProvider.get()
        ops = provider.get_ops("sed")
        palette = [
            "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
            "#a65628", "#f781bf", "#999999", "#1b9e77", "#d95f02",
        ]

        for i, row in enumerate(selected_rows):
            sed_id = row.get("id_")
            if sed_id is None:
                continue
            try:
                sed = ops.get_row(int(sed_id))
                fig.add_trace(
                    go.Scatter(
                        x=sed.sed_wavelengths,
                        y=sed.sed_values,
                        mode="lines",
                        name=sed.name,
                        line=dict(color=palette[i % len(palette)]),
                    )
                )
            except Exception:
                pass

    fig.update_layout(
        xaxis_title="Wavelength (nm)",
        yaxis_title="SED Value",
        template="plotly_white",
        margin=dict(t=10, b=40, l=50, r=10),
    )
    return fig
