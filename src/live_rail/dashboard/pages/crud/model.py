"""CRUD page for Model."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="model",
    display_name="Models",
    response_model=models.Model,
    create_model=models.ModelCreate,
    table_columns=["id_", "name", "algo_id", "catalog_tag_id"],
    has_load=True,
    foreign_keys={"algo_name": "algorithm", "catalog_tag_name": "catalog_tag"},
)

dash.register_page(__name__, path="/crud/model", name="Models")
layout = make_crud_layout(config)
register_crud_callbacks(config)
