"""Tests for CRUD UI component builders."""

import dash_ag_grid as dag
from dash import dcc, html
from pydantic import BaseModel, Field

from live_rail.dashboard.pages.crud._components import (
    build_action_bar,
    build_create_modal,
    build_data_table,
    build_detail_modal,
    build_filter_bar,
    build_form_fields,
)


class SampleCreate(BaseModel):
    name: str = Field(..., description="The name")
    count: int = Field(..., description="A count")
    flag: bool = Field(default=False)
    config: dict | None = Field(None, description="Optional config")


class TestBuildFilterBar:
    def test_returns_div_with_input(self):
        result = build_filter_bar("algo")
        assert isinstance(result, html.Div)
        input_el = result.children[0]
        assert input_el.id == "algo-filter-input"
        assert input_el.type == "text"

    def test_placeholder_text(self):
        result = build_filter_bar("test")
        assert result.children[0].placeholder == "Filter rows..."


class TestBuildDataTable:
    def test_returns_ag_grid(self):
        table = build_data_table("my-table", ["id_", "name", "model_id"])
        assert isinstance(table, dag.AgGrid)
        assert table.id == "my-table"

    def test_columns_match_input(self):
        table = build_data_table("my-table", ["id_", "name", "model_id"])
        fields = [c["field"] for c in table.columnDefs]
        assert fields == ["id_", "name", "model_id"]

    def test_clickable_style_for_name(self):
        table = build_data_table("t", ["id_", "name", "value"])
        styled_cols = [c["field"] for c in table.columnDefs if "cellStyle" in c]
        assert "name" in styled_cols

    def test_clickable_style_for_fk_columns(self):
        table = build_data_table("t", ["id_", "name", "model_id", "dataset_id"])
        styled_cols = [c["field"] for c in table.columnDefs if "cellStyle" in c]
        assert "model_id" in styled_cols
        assert "dataset_id" in styled_cols
        assert "id_" not in styled_cols

    def test_pagination_enabled(self):
        table = build_data_table("t", ["id_"])
        assert table.dashGridOptions["pagination"] is True
        assert table.dashGridOptions["paginationPageSize"] == 20

    def test_single_row_selection_with_deselect(self):
        table = build_data_table("t", ["id_"])
        sel = table.dashGridOptions["rowSelection"]
        assert sel["mode"] == "singleRow"
        assert sel["enableDeselection"] is True


class TestBuildDetailModal:
    def test_has_required_ids(self):
        result = build_detail_modal("algo")

        def collect_ids(component, found=None):
            if found is None:
                found = []
            if hasattr(component, "id") and component.id:
                found.append(component.id)
            children = getattr(component, "children", None)
            if isinstance(children, list):
                for c in children:
                    collect_ids(c, found)
            elif hasattr(children, "id"):
                collect_ids(children, found)
            return found

        ids = collect_ids(result)
        assert "algo-detail-modal" in ids
        assert "algo-detail-title" in ids
        assert "algo-detail-content" in ids
        assert "algo-detail-close" in ids

    def test_starts_hidden(self):
        result = build_detail_modal("x")
        assert result.style["display"] == "none"


class TestBuildFormFields:
    def test_generates_fields_for_all_model_fields(self):
        fields = build_form_fields(SampleCreate, "test")
        assert len(fields) == 4

    def test_str_field_is_text_input(self):
        fields = build_form_fields(SampleCreate, "t")
        name_field = fields[0]
        input_el = name_field.children[1]
        assert isinstance(input_el, dcc.Input)
        assert input_el.type == "text"

    def test_int_field_is_number_input(self):
        fields = build_form_fields(SampleCreate, "t")
        count_field = fields[1]
        input_el = count_field.children[1]
        assert isinstance(input_el, dcc.Input)
        assert input_el.type == "number"

    def test_bool_field_is_checklist(self):
        fields = build_form_fields(SampleCreate, "t")
        flag_field = fields[2]
        input_el = flag_field.children[1]
        assert isinstance(input_el, dcc.Checklist)

    def test_dict_field_is_textarea(self):
        fields = build_form_fields(SampleCreate, "t")
        config_field = fields[3]
        input_el = config_field.children[1]
        assert isinstance(input_el, dcc.Textarea)

    def test_fk_field_is_dropdown(self):
        fields = build_form_fields(SampleCreate, "t", foreign_keys={"name": "algorithm"})
        name_field = fields[0]
        input_el = name_field.children[1]
        assert isinstance(input_el, dcc.Dropdown)

    def test_required_field_has_asterisk(self):
        fields = build_form_fields(SampleCreate, "t")
        name_label = fields[0].children[0]
        assert "*" in name_label.children


class TestBuildCreateModal:
    def test_has_submit_button(self):
        result = build_create_modal("algo", SampleCreate)

        def find_by_id(component, target_id):
            if hasattr(component, "id") and component.id == target_id:
                return component
            children = getattr(component, "children", None)
            if isinstance(children, list):
                for c in children:
                    r = find_by_id(c, target_id)
                    if r:
                        return r
            elif hasattr(children, "id"):
                return find_by_id(children, target_id)
            return None

        assert find_by_id(result, "algo-create-submit") is not None

    def test_starts_hidden(self):
        result = build_create_modal("x", SampleCreate)
        assert result.style["display"] == "none"


class TestBuildActionBar:
    def test_has_refresh_create_delete(self):
        result = build_action_bar("algo")
        ids = [c.id for c in result.children if hasattr(c, "id")]
        assert "algo-refresh-btn" in ids
        assert "algo-create-btn" in ids
        assert "algo-delete-btn" in ids

    def test_no_load_button_by_default(self):
        result = build_action_bar("algo")
        ids = [c.id for c in result.children if hasattr(c, "id")]
        assert "algo-load-btn" not in ids

    def test_has_load_button_when_requested(self):
        result = build_action_bar("ds", has_load=True)
        ids = [c.id for c in result.children if hasattr(c, "id")]
        assert "ds-load-btn" in ids
