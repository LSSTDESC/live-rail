"""CRUD page for Band."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="band",
    display_name="Bands",
    response_model=models.Band,
    create_model=models.BandCreate,
    table_columns=["id_", "name"],
)

dash.register_page(__name__, path="/crud/band", name="Bands")
layout = make_crud_layout(config)
register_crud_callbacks(config)
