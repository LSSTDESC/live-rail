"""CRUD page for CatalogTag with band transmission visualization."""

import dash
import plotly.graph_objs as go
from dash import Input, Output, callback, dcc, html
from rail_svc import models

from live_rail.backend import BackendProvider
from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="catalog_tag",
    display_name="Catalog Tags",
    response_model=models.CatalogTag,
    create_model=models.CatalogTagCreate,
    table_columns=["id_", "name"],
    multi_select=True,
    extra_layout=[
        html.Div(
            [
                html.H4("Associated Band Transmission Curves", style={"marginTop": "16px"}),
                dcc.Graph(
                    id="catalog-tag-band-plot",
                    config={"responsive": True},
                    style={"height": "350px"},
                    figure=go.Figure().update_layout(
                        xaxis_title="Wavelength (nm)",
                        yaxis_title="Transmission",
                        template="plotly_white",
                        margin=dict(t=10, b=40, l=50, r=10),
                    ),
                ),
            ],
        ),
    ],
)

dash.register_page(__name__, path="/crud/catalog-tag", name="Catalog Tags")
layout = make_crud_layout(config)
register_crud_callbacks(config)


@callback(
    Output("catalog-tag-band-plot", "figure"),
    Input("catalog_tag-table", "selectedRows"),
)
def update_band_plot(selected_rows):
    fig = go.Figure()

    if selected_rows:
        provider = BackendProvider.get()
        palette = [
            "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
            "#a65628", "#f781bf", "#999999", "#1b9e77", "#d95f02",
        ]
        color_idx = 0
        seen_band_ids = set()

        for row in selected_rows:
            tag_id = row.get("id_")
            if tag_id is None:
                continue
            assocs = provider.catalog_band_assoc.find_by(catalog_tag_id=int(tag_id))
            for assoc in assocs:
                if assoc.band_id in seen_band_ids:
                    continue
                seen_band_ids.add(assoc.band_id)
                try:
                    band = provider.band.get_row(assoc.band_id)
                    fig.add_trace(
                        go.Scatter(
                            x=band.band_wavelengths,
                            y=band.band_transmission,
                            mode="lines",
                            name=band.name,
                            line=dict(color=palette[color_idx % len(palette)]),
                        )
                    )
                    color_idx += 1
                except Exception:
                    pass

    fig.update_layout(
        xaxis_title="Wavelength (nm)",
        yaxis_title="Transmission",
        template="plotly_white",
        margin=dict(t=10, b=40, l=50, r=10),
    )
    return fig
