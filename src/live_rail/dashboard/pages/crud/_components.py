"""Reusable CRUD UI components: data table, form generation, modals."""

from __future__ import annotations

from typing import Any

import dash_ag_grid as dag
from dash import dcc, html
from pydantic import BaseModel


def build_filter_bar(prefix: str) -> html.Div:
    """Create a simple text filter input for the table."""
    return html.Div(
        [
            dcc.Input(
                id=f"{prefix}-filter-input",
                type="text",
                placeholder="Filter rows...",
                debounce=True,
                style={
                    "width": "250px",
                    "padding": "6px 10px",
                    "fontSize": "13px",
                    "border": "1px solid #ccc",
                    "borderRadius": "4px",
                },
            ),
        ],
        style={"marginBottom": "10px"},
    )


def build_data_table(table_id: str, columns: list[str], multi_select: bool = False) -> dag.AgGrid:
    """Create a configured AG Grid for entity display."""
    clickable_cols = {c for c in columns if c == "name" or (c.endswith("_id") and c != "id_")}

    column_defs = []
    for col in columns:
        col_def: dict[str, Any] = {"field": col, "headerName": col, "sortable": True, "filter": True}
        if col in clickable_cols:
            col_def["cellStyle"] = {"color": "#0066cc", "cursor": "pointer", "textDecoration": "underline"}
        column_defs.append(col_def)

    if multi_select:
        row_selection = {
            "mode": "multiRow",
            "checkboxes": True,
            "headerCheckbox": True,
            "enableDeselection": True,
        }
    else:
        row_selection = {"mode": "singleRow", "checkboxes": True, "enableDeselection": True}

    return dag.AgGrid(
        id=table_id,
        columnDefs=column_defs,
        rowData=[],
        defaultColDef={"resizable": True, "flex": 1, "minWidth": 80},
        dashGridOptions={
            "rowSelection": row_selection,
            "pagination": True,
            "paginationPageSize": 20,
            "animateRows": True,
        },
        style={"height": "400px"},
    )


def build_detail_modal(prefix: str) -> html.Div:
    """Build a modal for displaying full row details."""
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(id=f"{prefix}-detail-title"),
                            html.Button(
                                "X",
                                id=f"{prefix}-detail-close",
                                style={
                                    "float": "right",
                                    "border": "none",
                                    "fontSize": "18px",
                                    "cursor": "pointer",
                                    "background": "none",
                                },
                            ),
                        ],
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                    ),
                    html.Hr(),
                    html.Div(id=f"{prefix}-detail-content"),
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "24px",
                    "borderRadius": "8px",
                    "maxWidth": "600px",
                    "margin": "60px auto",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                    "maxHeight": "80vh",
                    "overflowY": "auto",
                },
            ),
        ],
        id=f"{prefix}-detail-modal",
        style={
            "display": "none",
            "position": "fixed",
            "top": 0,
            "left": 0,
            "right": 0,
            "bottom": 0,
            "backgroundColor": "rgba(0,0,0,0.5)",
            "zIndex": 1000,
        },
    )


def build_form_fields(
    create_model: type[BaseModel],
    prefix: str,
    foreign_keys: dict[str, str] | None = None,
) -> list[html.Div]:
    """Auto-generate form fields from a pydantic model's field definitions."""
    fields = []
    fk_map = foreign_keys or {}

    for name, field_info in create_model.model_fields.items():
        field_id = f"{prefix}-field-{name}"
        label = name.replace("_", " ").title()
        description = field_info.description or ""

        annotation = field_info.annotation
        input_el: Any
        if name in fk_map:
            input_el = dcc.Dropdown(id=field_id, placeholder=f"Select {label}...")
        elif annotation is bool:
            input_el = dcc.Checklist(
                id=field_id,
                options=[{"label": label, "value": "true"}],
                value=["true"] if field_info.default else [],
            )
        elif annotation is int:
            input_el = dcc.Input(id=field_id, type="number", placeholder=description)
        elif annotation is dict or str(annotation).startswith("dict"):
            input_el = dcc.Textarea(
                id=field_id,
                placeholder='JSON: {"key": "value"}',
                style={"width": "100%", "height": "60px"},
            )
        else:
            input_el = dcc.Input(
                id=field_id,
                type="text",
                placeholder=description,
                style={"width": "100%"},
            )

        is_required = field_info.is_required()
        label_text = f"{label} *" if is_required else label

        fields.append(
            html.Div(
                [
                    html.Label(label_text, style={"fontSize": "12px", "fontWeight": "500"}),
                    input_el,
                ],
                style={"marginBottom": "12px"},
            )
        )

    return fields


def build_create_modal(
    entity_name: str,
    create_model: type[BaseModel],
    foreign_keys: dict[str, str] | None = None,
) -> html.Div:
    """Build a modal dialog for creating a new entity."""
    prefix = entity_name
    form_fields = build_form_fields(create_model, prefix, foreign_keys)

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(f"Create {entity_name.replace('_', ' ').title()}"),
                            html.Button(
                                "X",
                                id=f"{prefix}-modal-close",
                                style={"float": "right", "border": "none", "fontSize": "18px"},
                            ),
                        ],
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                    ),
                    html.Hr(),
                    *form_fields,
                    html.Hr(),
                    html.Button(
                        "Create",
                        id=f"{prefix}-create-submit",
                        style={
                            "padding": "8px 24px",
                            "backgroundColor": "#007bff",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "4px",
                        },
                    ),
                    html.Div(id=f"{prefix}-create-status", style={"marginTop": "8px"}),
                ],
                style={
                    "backgroundColor": "white",
                    "padding": "24px",
                    "borderRadius": "8px",
                    "maxWidth": "500px",
                    "margin": "60px auto",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                },
            ),
        ],
        id=f"{prefix}-create-modal",
        style={
            "display": "none",
            "position": "fixed",
            "top": 0,
            "left": 0,
            "right": 0,
            "bottom": 0,
            "backgroundColor": "rgba(0,0,0,0.5)",
            "zIndex": 1000,
        },
    )


def build_action_bar(entity_name: str, has_load: bool = False) -> html.Div:
    """Build the action bar with Create/Delete/Refresh buttons."""
    prefix = entity_name
    buttons = [
        html.Button(
            "Refresh",
            id=f"{prefix}-refresh-btn",
            n_clicks=0,
            style={"padding": "6px 16px", "marginRight": "8px"},
        ),
        html.Button(
            "+ Create",
            id=f"{prefix}-create-btn",
            n_clicks=0,
            style={
                "padding": "6px 16px",
                "marginRight": "8px",
                "backgroundColor": "#28a745",
                "color": "white",
                "border": "none",
                "borderRadius": "4px",
            },
        ),
        html.Button(
            "Delete Selected",
            id=f"{prefix}-delete-btn",
            n_clicks=0,
            style={
                "padding": "6px 16px",
                "backgroundColor": "#dc3545",
                "color": "white",
                "border": "none",
                "borderRadius": "4px",
            },
        ),
    ]

    if has_load:
        buttons.insert(
            2,
            html.Button(
                "Load",
                id=f"{prefix}-load-btn",
                n_clicks=0,
                style={
                    "padding": "6px 16px",
                    "marginRight": "8px",
                    "backgroundColor": "#17a2b8",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "4px",
                },
            ),
        )

    return html.Div(buttons, style={"marginBottom": "12px"})
