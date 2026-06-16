"""CRUD page for Estimator."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="estimator",
    display_name="Estimators",
    response_model=models.Estimator,
    create_model=models.EstimatorCreate,
    table_columns=["id_", "name", "model_id"],
    foreign_keys={"model_name": "model"},
)

dash.register_page(__name__, path="/crud/estimator", name="Estimators")
layout = make_crud_layout(config)
register_crud_callbacks(config)
