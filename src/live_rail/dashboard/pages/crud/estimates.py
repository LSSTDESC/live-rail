"""CRUD page for Estimates."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="estimates",
    display_name="Estimates",
    response_model=models.Estimates,
    create_model=models.EstimatesCreate,
    table_columns=["id_", "name", "n_objects", "estimator_id", "dataset_id"],
    has_load=True,
)

dash.register_page(__name__, path="/crud/estimates", name="Estimates")
layout = make_crud_layout(config)
register_crud_callbacks(config)
