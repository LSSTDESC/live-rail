"""CRUD page for CatalogBandAssoc."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="catalog_band_assoc",
    display_name="Catalog Band Associations",
    response_model=models.CatalogBandAssoc,
    create_model=models.CatalogBandAssocCreate,
    table_columns=["id_", "mag_column_name", "mag_err_column_name", "catalog_tag_id", "band_id"],
    foreign_keys={"catalog_tag_name": "catalog_tag", "band_name": "band"},
)

dash.register_page(__name__, path="/crud/catalog-band-assoc", name="Band Associations")
layout = make_crud_layout(config)
register_crud_callbacks(config)
