import os
from pathlib import Path
import urllib
from rail.utils import catalog_utils, path_utils
from rail_svc import db, local_sync
import subprocess

import live_rail
from live_rail import rail_svc_utils

FILTER_DIR = Path(path_utils.RAILDIR) / 'rail/examples_data/estimation_data/data/FILTER'
SANDBOX_CATALOG_YAML = Path(os.path.dirname(live_rail.__file__).replace('src/live_rail', 'nb')) / 'sandbox_catalogs.yaml'
BASE_DIR = Path(os.environ.get("PZ_RAIL_DATA_DIR", '.'))
TEST_DATA_DIR = BASE_DIR / Path('data/test/')
MODEL_DIR = BASE_DIR / Path('projects/sandbox/data')
ESTIMATES_DIR = BASE_DIR / Path('projects/sandbox/data')

ALGOS = {
    'knn':'rail.estimation.algos.k_nearneigh.KNearNeighEstimator',
    'fzboost':'rail.estimation.algos.flexzboost.FlexZBoostEstimator',
    'tpz':'rail.estimation.algos.tpz_lite.TPZliteEstimator',
    'cmnn':'rail.estimation.algos.cmnn.CMNNEstimator',
    'lephare':'rail.estimation.algos.lephare.LephareEstimator',
    'bpz':'rail.estimation.algos.bpz_lite.BPZliteEstimator',
    'gpz':'rail.estimation.algos.gpz.GPzEstimator',
    'dnf':'rail.estimation.algos.dnf.DNFEstimator',
}



def download_data():

    tar_file = 'sandbox.tgz'
    if not os.path.exists(tar_file):
        urllib.request.urlretrieve(
            "http://s3df.slac.stanford.edu/people/echarles/sandbox.tgz",
            'sandbox.tgz'
        )
        if not os.path.exists(tar_file):
            return 1

    print(f"look for {str(MODEL_DIR/ 'flagship_gold_roman_1yr' / 'model_inform_knn.pkl')}")
    if not os.path.exists(MODEL_DIR/ 'flagship_gold_roman_1yr' / 'model_inform_knn.pkl'):
        print(f"unpack to {BASE_DIR}")
        status = subprocess.run(
            ["tar", "zxvf", tar_file, "-C", BASE_DIR], check=False
        )
        if status.returncode != 0:
            return status.returncode

    if not os.path.exists(MODEL_DIR/'flagship_gold_roman_1yr' / 'model_inform_knn.pkl'):
        return 2

    try:
        os.makedirs('archive')
        status = subprocess.run(
            ["ln", "-s", str(BASE_DIR / pz), "archive/pz"]
        )
    except:
        pass


def load():
    
    for cat in ['roman', 'rubin']:
        rail_svc_utils.safe_insert_catalog_tag(cat)

    for ver in ['10yr', '1yr']:
        dataset_names = []
        for cat in ['roman', 'rubin']:
            dataset_name = f'sandbox_{cat}_{ver}'
            dataset_names.append(dataset_name)
            dataset_file = str(TEST_DATA_DIR / Path(f'sandbox_test_{cat}_{ver}.hdf5'))
            catalog_tag_name = cat
            rail_svc_utils.safe_insert_dataset(dataset_name, dataset_file, catalog_tag_name, n_objects=40000, is_collection=False, validate_file=False)

        matched_dataset_name = f'sandbox_roman_plus_rubin_{ver}'
        catalog_tag_name = 'roman_plus_rubin'
        dataset_file = str(TEST_DATA_DIR / Path(f'sandbox_test_{catalog_tag_name}_{ver}.hdf5'))
        rail_svc_utils.safe_insert_matched_dataset(matched_dataset_name, catalog_tag_name, dataset_names, dataset_file, n_objects=40000)

    for k, v in ALGOS.items():
        algo = k
        rail_svc_utils.safe_insert_algo(name=algo, class_name=v)    
        for cat in ['roman', 'rubin', 'roman_plus_rubin']:
            for ver in ['10yr', '1yr']:
                catalog_tag_name = cat
                model_name = f'sandbox_{algo}_{cat}_{ver}'
                dataset_name = f'sandbox_{cat}_{ver}'
                estimator_name = f'sandbox_{algo}_{cat}_{ver}'
                estimates_name = f'sandbox_{algo}_{cat}_{ver}'
                model_file = str(MODEL_DIR / f'flagship_gold_{cat}_{ver}' /f'model_inform_{algo}.pkl')
                qp_file = str(ESTIMATES_DIR / f'flagship_gold_{cat}_{ver}' / f'output_estimate_{algo}.hdf5')
                rail_svc_utils.safe_insert_algo(name=algo, class_name=v)
                if algo not in ['bpz', 'fzboost', 'gpz', 'knn']:
                    continue
                rail_svc_utils.safe_insert_model(model_name, model_file, algo, catalog_tag_name, validate_file=False)
                rail_svc_utils.safe_insert_estimator(estimator_name, model_name)
                rail_svc_utils.safe_insert_estimates(estimates_name, qp_file, estimator_name, dataset_name, n_objects=40000, validate_file=False)


if __name__ == '__main__':
    download_data()
    # rail_svc_utils.setup_db()
    db.init_db()
    local_sync.funcs.load_catalog_yaml(SANDBOX_CATALOG_YAML, filter_dir=FILTER_DIR)
    load()
