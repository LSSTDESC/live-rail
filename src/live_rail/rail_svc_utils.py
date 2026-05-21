
import subprocess

from rail_svc import local_sync

    
def safe_insert_catalog_tag(name):
    try:
        local_sync.catalog_tag.get_row_by_name(name)
    except:
        local_sync.catalog_tag.create_row(name=name)

def safe_insert_dataset(name, path, catalog_tag_name, **kwargs):
    try:
        local_sync.dataset.get_row_by_name(name)
    except:
        local_sync.dataset.create_row(name=name, path=path, catalog_tag_name=catalog_tag_name, **kwargs)

def safe_insert_algo(name, class_name):
    try:
        local_sync.algorithm.get_row_by_name(name)
    except:
        local_sync.algorithm.create_row(name=name, class_name=class_name)

def safe_insert_model(name, path, algo_name, catalog_tag_name, **kwargs):
    try:
        local_sync.model.get_row_by_name(name)
    except:
        local_sync.model.create_row(name=name, path=path, algo_name=algo_name, catalog_tag_name=catalog_tag_name, **kwargs)

def safe_insert_estimator(name, model_name, **kwargs):
    try:
        local_sync.estimator.get_row_by_name(name)
    except:
        local_sync.estimator.create_row(name=name, model_name=model_name, config=kwargs)

def safe_insert_estimates(name, path, estimator_name, dataset_name, **kwargs):
    try:
        local_sync.estimates.get_row_by_name(name)
    except:
        local_sync.estimates.create_row(
            name=name, path=path, estimator_name=estimator_name, dataset_name=dataset_name, **kwargs
        )

def safe_insert_matched_dataset(name, catalog_tag_name, component_dataset_names, path, n_objects):
    try:
        local_sync.dataset.get_row_by_name(name)
    except:
        local_sync.funcs.create_matched_dataset(
            name, catalog_tag_name, component_dataset_names=component_dataset_names, path=path, n_objects=n_objects,
        )


def setup_db() -> int:
    
    status = subprocess.run(
        ["pz-rail-svc-local", "init", "--reset"]
    )
    return status.returncode
