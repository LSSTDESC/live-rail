"""Tests for CRUD base module: serialization, detail content, config, filter logic."""


from dash import html
from pydantic import BaseModel, ConfigDict, Field

from live_rail.dashboard.pages.crud._base import (
    FK_COLUMN_MAP,
    CrudPageConfig,
    _build_detail_content,
    _serialize_value,
)


class SampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_: int = Field(...)
    name: str = Field(...)
    path: str | None = Field(None)
    count: int = Field(default=0)


class SampleCreate(BaseModel):
    name: str = Field(...)


class TestSerializeValue:
    def test_none(self):
        assert _serialize_value(None) is None

    def test_string(self):
        assert _serialize_value("hello") == "hello"

    def test_int(self):
        assert _serialize_value(42) == 42

    def test_float(self):
        assert _serialize_value(3.14) == 3.14

    def test_bool(self):
        assert _serialize_value(True) is True

    def test_dict_becomes_str(self):
        result = _serialize_value({"key": "val"})
        assert isinstance(result, str)
        assert "key" in result

    def test_list_becomes_str(self):
        result = _serialize_value([1, 2, 3])
        assert isinstance(result, str)
        assert "1" in result


class TestBuildDetailContent:
    def test_generates_div_for_each_field(self):
        row = SampleResponse(id_=1, name="test", path="/a/b", count=5)
        content = _build_detail_content(row)
        assert isinstance(content, html.Div)
        assert len(content.children) == 4

    def test_field_names_shown(self):
        row = SampleResponse(id_=1, name="algo1", path=None, count=0)
        content = _build_detail_content(row)
        labels = [c.children[0].children for c in content.children]
        assert "name" in labels
        assert "path" in labels
        assert "id_" in labels

    def test_none_field_shows_dash(self):
        row = SampleResponse(id_=1, name="x", path=None, count=0)
        content = _build_detail_content(row)
        # path is the 3rd field
        path_item = [c for c in content.children if c.children[0].children == "path"][0]
        assert path_item.children[1].children == "—"


class TestFKColumnMap:
    def test_has_model_id(self):
        assert FK_COLUMN_MAP["model_id"] == "model"

    def test_has_dataset_id(self):
        assert FK_COLUMN_MAP["dataset_id"] == "dataset"

    def test_has_catalog_tag_id(self):
        assert FK_COLUMN_MAP["catalog_tag_id"] == "catalog_tag"

    def test_has_estimator_id(self):
        assert FK_COLUMN_MAP["estimator_id"] == "estimator"

    def test_has_algo_id(self):
        assert FK_COLUMN_MAP["algo_id"] == "algorithm"

    def test_has_band_id(self):
        assert FK_COLUMN_MAP["band_id"] == "band"


class TestCrudPageConfig:
    def test_required_fields(self):
        config = CrudPageConfig(
            entity_name="algorithm",
            display_name="Algorithms",
            response_model=SampleResponse,
            create_model=SampleCreate,
            table_columns=["id_", "name"],
        )
        assert config.entity_name == "algorithm"
        assert config.has_load is False
        assert config.has_download is False
        assert config.foreign_keys == {}

    def test_optional_fields(self):
        config = CrudPageConfig(
            entity_name="dataset",
            display_name="Datasets",
            response_model=SampleResponse,
            create_model=SampleCreate,
            table_columns=["id_", "name"],
            has_load=True,
            foreign_keys={"catalog_tag_name": "catalog_tag"},
        )
        assert config.has_load is True
        assert "catalog_tag_name" in config.foreign_keys


class TestFilterLogic:
    """Test the filtering logic used in the filter_table callback."""

    def _filter(self, filter_text, all_data):
        """Replicate the filter logic from register_crud_callbacks."""
        if not all_data:
            return []
        if not filter_text:
            return all_data
        query = filter_text.lower()
        return [
            row for row in all_data
            if any(query in str(v).lower() for v in row.values() if v is not None)
        ]

    def test_empty_data_returns_empty(self):
        assert self._filter("test", []) == []

    def test_no_filter_returns_all(self):
        data = [{"name": "a"}, {"name": "b"}]
        assert self._filter("", data) == data
        assert self._filter(None, data) == data

    def test_substring_match(self):
        data = [{"name": "knn"}, {"name": "bpz"}, {"name": "flexzboost"}]
        result = self._filter("knn", data)
        assert len(result) == 1
        assert result[0]["name"] == "knn"

    def test_case_insensitive(self):
        data = [{"name": "KNN"}, {"name": "bpz"}]
        result = self._filter("knn", data)
        assert len(result) == 1

    def test_matches_any_column(self):
        data = [{"id_": 1, "name": "algo", "class": "rail.knn"}]
        result = self._filter("rail", data)
        assert len(result) == 1

    def test_no_matches(self):
        data = [{"name": "knn"}, {"name": "bpz"}]
        result = self._filter("xyz", data)
        assert len(result) == 0

    def test_numeric_match(self):
        data = [{"id_": 42, "name": "test"}]
        result = self._filter("42", data)
        assert len(result) == 1
