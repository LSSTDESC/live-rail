"""CRUD page for FilterAB with multi-select and flux vs redshift visualization."""

import dash
import plotly.graph_objs as go
from dash import Input, Output, callback, dcc, html
from rail_svc import models

from live_rail.backend import BackendProvider
from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="filter_ab",
    display_name="Filter AB",
    response_model=models.FilterAB,
    create_model=models.FilterABCreate,
    table_columns=["id_", "name", "band_id", "sed_id"],
    multi_select=True,
    foreign_keys={"band_name": "band", "sed_name": "sed"},
    extra_layout=[
        html.Div(
            [
                html.H4("AB Flux vs Redshift", style={"marginTop": "16px"}),
                dcc.Graph(
                    id="filter-ab-flux-plot",
                    config={"responsive": True},
                    style={"height": "350px"},
                    figure=go.Figure().update_layout(
                        xaxis_title="Redshift",
                        yaxis_title="Flux",
                        template="plotly_white",
                        margin=dict(t=10, b=40, l=50, r=10),
                    ),
                ),
            ],
        ),
    ],
)

dash.register_page(__name__, path="/crud/filter-ab", name="Filter AB")
layout = make_crud_layout(config)
register_crud_callbacks(config)


@callback(
    Output("filter-ab-flux-plot", "figure"),
    Input("filter_ab-table", "selectedRows"),
)
def update_filter_ab_plot(selected_rows):
    fig = go.Figure()

    if selected_rows:
        provider = BackendProvider.get()
        ops = provider.get_ops("filter_ab")
        palette = [
            "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
            "#a65628", "#f781bf", "#999999", "#1b9e77", "#d95f02",
        ]

        for i, row in enumerate(selected_rows):
            fab_id = row.get("id_")
            if fab_id is None:
                continue
            try:
                fab = ops.get_row(int(fab_id))
                fig.add_trace(
                    go.Scatter(
                        x=fab.redshifts,
                        y=fab.fluxes,
                        mode="lines",
                        name=fab.name,
                        line=dict(color=palette[i % len(palette)]),
                    )
                )
            except Exception:
                pass

    fig.update_layout(
        xaxis_title="Redshift",
        yaxis_title="Flux",
        template="plotly_white",
        margin=dict(t=10, b=40, l=50, r=10),
    )
    return fig
