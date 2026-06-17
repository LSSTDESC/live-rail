"""CRUD page factory: generates a complete page layout + callbacks from config."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from dash import Input, Output, State, callback, ctx, dcc, html, no_update
from pydantic import BaseModel

from live_rail.backend import BackendProvider
from live_rail.dashboard.pages.crud._components import (
    build_action_bar,
    build_create_modal,
    build_data_table,
    build_detail_modal,
    build_filter_bar,
)


def _serialize_value(val: Any) -> Any:
    """Convert non-JSON-serializable values to strings for the DataTable."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    return str(val)


def _build_detail_content(row: Any) -> html.Div:
    """Build a formatted display of all fields on a pydantic model instance."""
    items = []
    for field_name in type(row).model_fields:
        value = getattr(row, field_name, None)
        display_val = str(value) if value is not None else "—"
        items.append(
            html.Div(
                [
                    html.Span(
                        field_name,
                        style={
                            "fontWeight": "600",
                            "width": "160px",
                            "display": "inline-block",
                            "color": "#555",
                            "fontSize": "13px",
                        },
                    ),
                    html.Span(
                        display_val,
                        style={"fontSize": "13px", "wordBreak": "break-all"},
                    ),
                ],
                style={"padding": "6px 0", "borderBottom": "1px solid #f0f0f0"},
            )
        )
    return html.Div(items)


FK_COLUMN_MAP = {
    "model_id": "model",
    "dataset_id": "dataset",
    "catalog_tag_id": "catalog_tag",
    "estimator_id": "estimator",
    "algo_id": "algorithm",
    "band_id": "band",
    "matched_dataset_id": "dataset",
    "component_dataset_id": "dataset",
}


@dataclass
class CrudPageConfig:
    entity_name: str
    display_name: str
    response_model: type[BaseModel]
    create_model: type[BaseModel]
    table_columns: list[str]
    has_load: bool = False
    has_download: bool = False
    foreign_keys: dict[str, str] = field(default_factory=dict)


def make_crud_layout(config: CrudPageConfig):
    """Generate the page layout function for a CRUD entity."""
    prefix = config.entity_name

    def layout_fn(**kwargs):
        return html.Div(
            [
                html.H2(config.display_name),
                html.Hr(),
                build_action_bar(prefix, has_load=config.has_load),
                html.Div(id=f"{prefix}-status", style={"marginBottom": "8px"}),
                build_filter_bar(prefix),
                build_data_table(f"{prefix}-table", config.table_columns),
                build_create_modal(prefix, config.create_model, config.foreign_keys),
                build_detail_modal(prefix),
                dcc.Store(id=f"{prefix}-all-data", data=[]),
            ]
        )

    return layout_fn


def register_crud_callbacks(config: CrudPageConfig) -> None:
    """Register all Dash callbacks for a CRUD page."""
    prefix = config.entity_name

    # Refresh / load table data into store
    @callback(
        Output(f"{prefix}-all-data", "data"),
        Input(f"{prefix}-refresh-btn", "n_clicks"),
        prevent_initial_call=False,
    )
    def refresh_table(n_clicks):
        try:
            ops = BackendProvider.get().get_ops(config.entity_name)
            rows = ops.get_rows()
            return [
                {col: _serialize_value(getattr(row, col, None)) for col in config.table_columns}
                for row in rows
            ]
        except Exception:
            return []

    # Filter rows based on search text
    @callback(
        Output(f"{prefix}-table", "rowData"),
        Input(f"{prefix}-filter-input", "value"),
        Input(f"{prefix}-all-data", "data"),
    )
    def filter_table(filter_text, all_data):
        if not all_data:
            return []
        if not filter_text:
            return all_data
        query = filter_text.lower()
        return [
            row for row in all_data if any(query in str(v).lower() for v in row.values() if v is not None)
        ]

    # Show detail modal when a clickable cell is clicked
    @callback(
        Output(f"{prefix}-detail-modal", "style"),
        Output(f"{prefix}-detail-title", "children"),
        Output(f"{prefix}-detail-content", "children"),
        Input(f"{prefix}-table", "cellClicked"),
        Input(f"{prefix}-detail-close", "n_clicks"),
        State(f"{prefix}-table", "rowData"),
        State(f"{prefix}-detail-modal", "style"),
        prevent_initial_call=True,
    )
    def show_detail(cell_clicked, close_clicks, row_data_list, modal_style):

        triggered_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
        if "detail-close" in triggered_prop:
            return {**modal_style, "display": "none"}, no_update, no_update

        if not cell_clicked:
            return no_update, no_update, no_update

        col_id = cell_clicked.get("colId")
        row_index = cell_clicked.get("rowIndex")

        # Only open for clickable columns
        clickable = col_id == "name" or (col_id in FK_COLUMN_MAP)
        if not clickable:
            return no_update, no_update, no_update

        # Get the row data from the grid's rowData using rowIndex
        if row_data_list is None or row_index is None or row_index >= len(row_data_list):
            return no_update, no_update, no_update
        row_data = row_data_list[row_index]

        try:
            provider = BackendProvider.get()

            if col_id == "name":
                row_id = row_data.get("id_")
                ops = provider.get_ops(config.entity_name)
                full_row = ops.get_row(row_id)
                title = f"{config.display_name}: {getattr(full_row, 'name', row_id)}"
                content = _build_detail_content(full_row)
            else:
                ref_entity = FK_COLUMN_MAP[col_id]
                ref_id = row_data.get(col_id)
                if not ref_id:
                    return no_update, no_update, no_update
                ops = provider.get_ops(ref_entity)
                full_row = ops.get_row(int(ref_id))
                title = f"{ref_entity.replace('_', ' ').title()}: {getattr(full_row, 'name', ref_id)}"
                content = _build_detail_content(full_row)

        except Exception as e:
            title = "Error"
            content = html.P(f"Could not load details: {e}", style={"color": "red"})

        return {**modal_style, "display": "block"}, title, content

    # Toggle create modal
    @callback(
        Output(f"{prefix}-create-modal", "style"),
        Input(f"{prefix}-create-btn", "n_clicks"),
        Input(f"{prefix}-modal-close", "n_clicks"),
        State(f"{prefix}-create-modal", "style"),
        prevent_initial_call=True,
    )
    def toggle_modal(open_clicks, close_clicks, current_style):
        if ctx.triggered_id == f"{prefix}-create-btn":
            return {**current_style, "display": "block"}
        return {**current_style, "display": "none"}

    # Submit create form
    field_names = list(config.create_model.model_fields.keys())
    field_inputs = [State(f"{prefix}-field-{name}", "value") for name in field_names]

    @callback(
        Output(f"{prefix}-create-status", "children"),
        Output(f"{prefix}-refresh-btn", "n_clicks", allow_duplicate=True),
        Input(f"{prefix}-create-submit", "n_clicks"),
        *field_inputs,
        State(f"{prefix}-refresh-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def create_entity(n_clicks, *args):
        field_values = args[: len(field_names)]
        refresh_clicks = args[-1]

        kwargs = {}
        for name, value in zip(field_names, field_values):
            field_info = config.create_model.model_fields[name]
            if value is None or value == "" or value == []:
                if field_info.is_required():
                    return html.Span(f"Field '{name}' is required.", style={"color": "red"}), no_update
                continue

            annotation = field_info.annotation
            if annotation is bool or annotation is bool:
                kwargs[name] = bool(value)
            elif annotation is int or annotation is int:
                kwargs[name] = int(value)
            elif annotation is dict or str(annotation).startswith("dict"):
                try:
                    kwargs[name] = json.loads(value)
                except json.JSONDecodeError:
                    return html.Span(f"Invalid JSON for '{name}'.", style={"color": "red"}), no_update
            else:
                kwargs[name] = value

        try:
            ops = BackendProvider.get().get_ops(config.entity_name)
            result = ops.create_row(**kwargs)
            return (
                html.Span(f"Created: {getattr(result, 'name', result)}", style={"color": "green"}),
                (refresh_clicks or 0) + 1,
            )
        except Exception as e:
            return html.Span(f"Error: {e}", style={"color": "red"}), no_update

    # Delete selected row
    @callback(
        Output(f"{prefix}-status", "children"),
        Output(f"{prefix}-refresh-btn", "n_clicks", allow_duplicate=True),
        Input(f"{prefix}-delete-btn", "n_clicks"),
        State(f"{prefix}-table", "selectedRows"),
        State(f"{prefix}-refresh-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def delete_entity(n_clicks, selected_rows, refresh_clicks):
        if not selected_rows:
            return html.Span("No row selected.", style={"color": "orange"}), no_update

        row_data = selected_rows[0]
        row_id = row_data.get("id_")
        if row_id is None:
            return html.Span("Cannot determine row ID.", style={"color": "red"}), no_update

        try:
            ops = BackendProvider.get().get_ops(config.entity_name)
            ops.delete_row(row_id)
            return (
                html.Span(f"Deleted row {row_id}.", style={"color": "green"}),
                (refresh_clicks or 0) + 1,
            )
        except Exception as e:
            return html.Span(f"Error: {e}", style={"color": "red"}), no_update
