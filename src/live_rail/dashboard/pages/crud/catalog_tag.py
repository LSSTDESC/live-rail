"""CRUD page for CatalogTag."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="catalog_tag",
    display_name="Catalog Tags",
    response_model=models.CatalogTag,
    create_model=models.CatalogTagCreate,
    table_columns=["id_", "name"],
)

dash.register_page(__name__, path="/crud/catalog-tag", name="Catalog Tags")
layout = make_crud_layout(config)
register_crud_callbacks(config)
