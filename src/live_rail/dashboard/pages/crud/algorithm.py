"""CRUD page for Algorithm."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="algorithm",
    display_name="Algorithms",
    response_model=models.Algorithm,
    create_model=models.AlgorithmCreate,
    table_columns=["id_", "name", "class_name"],
)

dash.register_page(__name__, path="/crud/algorithm", name="Algorithms")
layout = make_crud_layout(config)
register_crud_callbacks(config)
