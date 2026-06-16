"""CRUD page for DatasetAssoc."""

import dash
from rail_svc import models

from live_rail.dashboard.pages.crud._base import CrudPageConfig, make_crud_layout, register_crud_callbacks

config = CrudPageConfig(
    entity_name="dataset_assoc",
    display_name="Dataset Associations",
    response_model=models.DatasetAssoc,
    create_model=models.DatasetAssocCreate,
    table_columns=["id_", "name", "matched_dataset_id", "component_dataset_id"],
)

dash.register_page(__name__, path="/crud/dataset-assoc", name="Dataset Associations")
layout = make_crud_layout(config)
register_crud_callbacks(config)
