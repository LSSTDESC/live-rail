"""CRUD page for Dataset with visualizer launch buttons."""

import dash
from dash import Input, Output, State, callback, dcc, html, no_update
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="dataset",
    display_name="Datasets",
    response_model=models.Dataset,
    create_model=models.DatasetCreate,
    table_columns=["id_", "name", "n_objects", "catalog_tag_id", "is_collection"],
    has_load=True,
    foreign_keys={"catalog_tag_name": "catalog_tag"},
)

dash.register_page(__name__, path="/crud/dataset", name="Datasets")


def layout(**kwargs):
    base = make_crud_layout(config)(**kwargs)
    viz_section = html.Div(
        [
            html.Button(
                "Visualize Single",
                id="dataset-viz-single-btn",
                n_clicks=0,
                disabled=True,
                style={
                    "padding": "6px 16px",
                    "marginRight": "8px",
                    "backgroundColor": "#6f42c1",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "4px",
                    "opacity": "0.5",
                },
            ),
            html.Button(
                "Visualize Multi",
                id="dataset-viz-multi-btn",
                n_clicks=0,
                disabled=True,
                style={
                    "padding": "6px 16px",
                    "backgroundColor": "#20c997",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "4px",
                    "opacity": "0.5",
                },
            ),
            dcc.Location(id="dataset-viz-redirect", refresh=True),
        ],
        style={"marginBottom": "12px"},
    )
    base.children.insert(4, viz_section)
    return base


register_crud_callbacks(config)


@callback(
    Output("dataset-viz-single-btn", "disabled"),
    Output("dataset-viz-single-btn", "style"),
    Output("dataset-viz-multi-btn", "disabled"),
    Output("dataset-viz-multi-btn", "style"),
    Input("dataset-table", "selectedRows"),
)
def update_viz_buttons(selected_rows):
    single_base = {
        "padding": "6px 16px",
        "marginRight": "8px",
        "backgroundColor": "#6f42c1",
        "color": "white",
        "border": "none",
        "borderRadius": "4px",
    }
    multi_base = {
        "padding": "6px 16px",
        "backgroundColor": "#20c997",
        "color": "white",
        "border": "none",
        "borderRadius": "4px",
    }

    if not selected_rows:
        return (
            True,
            {**single_base, "opacity": "0.5", "cursor": "not-allowed"},
            True,
            {**multi_base, "opacity": "0.5", "cursor": "not-allowed"},
        )

    row_data = selected_rows[0]
    is_collection = row_data.get("is_collection")

    single_style = {**single_base, "opacity": "1", "cursor": "pointer"}
    if is_collection:
        multi_style = {**multi_base, "opacity": "1", "cursor": "pointer"}
        multi_disabled = False
    else:
        multi_style = {**multi_base, "opacity": "0.5", "cursor": "not-allowed"}
        multi_disabled = True

    return False, single_style, multi_disabled, multi_style


@callback(
    Output("dataset-viz-redirect", "href"),
    Input("dataset-viz-single-btn", "n_clicks"),
    Input("dataset-viz-multi-btn", "n_clicks"),
    State("dataset-table", "selectedRows"),
    prevent_initial_call=True,
)
def launch_visualizer(single_clicks, multi_clicks, selected_rows):
    if not selected_rows:
        return no_update

    row_data = selected_rows[0]
    dataset_id = row_data.get("id_")

    ctx = dash.ctx
    if ctx.triggered_id == "dataset-viz-multi-btn":
        return f"/visualize/multi?dataset_id={dataset_id}"

    return f"/visualize/single?dataset_id={dataset_id}"
