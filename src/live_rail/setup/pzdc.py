"""PZDC (Photo-z Data Challenge) setup profile."""

from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

from rail.utils import catalog_utils

import live_rail
from live_rail import rail_svc_utils
from live_rail.setup import register
from live_rail.setup._base import SetupProfile

_BASE_DIR = Path(os.environ.get("PZ_RAIL_DATA_DIR", "./archive"))
_TEST_DATA_DIR = Path("data/test/")
_MODEL_DIR = Path("projects/sandbox/data")
_ESTIMATES_DIR = Path("projects/sandbox/data")

_SANDBOX_CATALOG_YAML = (
    Path(os.path.dirname(live_rail.__file__).replace("src/live_rail", "nb"))
    / "sandbox_catalogs.yaml"
)

_DATA_URL = "http://s3df.slac.stanford.edu/people/echarles/sandbox.tgz"

ALGOS = {
    "knn": "rail.estimation.algos.k_nearneigh.KNearNeighEstimator",
    "fzboost": "rail.estimation.algos.flexzboost.FlexZBoostEstimator",
    "tpz": "rail.estimation.algos.tpz_lite.TPZliteEstimator",
    "cmnn": "rail.estimation.algos.cmnn.CMNNEstimator",
    "lephare": "rail.estimation.algos.lephare.LephareEstimator",
    "bpz": "rail.estimation.algos.bpz_lite.BPZliteEstimator",
    "gpz": "rail.estimation.algos.gpz.GPzEstimator",
    "dnf": "rail.estimation.algos.dnf.DNFEstimator",
}

ACTIVE_ALGOS = {"bpz", "fzboost", "gpz", "knn"}


@register
class PzdcSetup(SetupProfile):
    """Setup profile for the PZDC sandbox dataset."""

    name = "pzdc"
    description = "Photo-z Data Challenge sandbox data (roman + rubin, 1yr + 10yr)"

    def get_catalog_yaml(self) -> Path:
        return _SANDBOX_CATALOG_YAML

    def download(self) -> None:
        os.makedirs(_BASE_DIR, exist_ok=True)

        tar_file = "sandbox.tgz"
        if not os.path.exists(tar_file):
            print(f"Downloading {_DATA_URL} ...")
            urllib.request.urlretrieve(_DATA_URL, tar_file)
            if not os.path.exists(tar_file):
                raise RuntimeError("Download failed: sandbox.tgz not created")

        marker = (
            _BASE_DIR / _MODEL_DIR / "flagship_gold_roman_1yr" / "model_inform_knn.pkl"
        )
        if not marker.exists():
            print(f"Extracting to {_BASE_DIR} ...")
            result = subprocess.run(
                ["tar", "zxvf", tar_file, "-C", str(_BASE_DIR)], check=False
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"tar extraction failed with code {result.returncode}"
                )

        if not marker.exists():
            raise RuntimeError(f"Expected file not found after extraction: {marker}")

    def load(self) -> None:

        sed_dir = Path(
            catalog_utils.find_rail_file("examples_data/estimation_data/data/SED")
        )

        filter_ab_dir = Path(
            catalog_utils.find_rail_file("examples_data/estimation_data/data/AB")
        )

        for cat in ["roman", "rubin"]:
            rail_svc_utils.safe_insert_catalog_tag(cat)

        rail_svc_utils.safe_load_seds(sed_dir)

        rail_svc_utils.safe_load_filter_abs(filter_ab_dir)

        for ver in ["10yr", "1yr"]:
            dataset_names = []
            for cat in ["roman", "rubin"]:
                dataset_name = f"sandbox_{cat}_{ver}"
                dataset_names.append(dataset_name)
                dataset_file = str(_TEST_DATA_DIR / f"sandbox_test_{cat}_{ver}.hdf5")
                rail_svc_utils.safe_insert_dataset(
                    dataset_name,
                    dataset_file,
                    cat,
                    n_objects=40000,
                    is_collection=False,
                    validate_file=False,
                )

            matched_name = f"sandbox_roman_plus_rubin_{ver}"
            matched_tag = "roman_plus_rubin"
            matched_file = str(
                _TEST_DATA_DIR / f"sandbox_test_{matched_tag}_{ver}.hdf5"
            )
            rail_svc_utils.safe_insert_matched_dataset(
                matched_name, matched_tag, dataset_names, matched_file, n_objects=40000
            )

        for algo_name, algo_class in ALGOS.items():
            rail_svc_utils.safe_insert_algo(name=algo_name, class_name=algo_class)
            if algo_name not in ACTIVE_ALGOS:
                continue

            for cat in ["roman", "rubin", "roman_plus_rubin"]:
                for ver in ["10yr", "1yr"]:
                    model_name = f"sandbox_{algo_name}_{cat}_{ver}"
                    dataset_name = f"sandbox_{cat}_{ver}"
                    estimator_name = f"sandbox_{algo_name}_{cat}_{ver}"
                    estimates_name = f"sandbox_{algo_name}_{cat}_{ver}"
                    model_file = str(
                        _MODEL_DIR
                        / f"flagship_gold_{cat}_{ver}"
                        / f"model_inform_{algo_name}.pkl"
                    )
                    qp_file = str(
                        _ESTIMATES_DIR
                        / f"flagship_gold_{cat}_{ver}"
                        / f"output_estimate_{algo_name}.hdf5"
                    )
                    rail_svc_utils.safe_insert_model(
                        model_name, model_file, algo_name, cat, validate_file=False
                    )
                    rail_svc_utils.safe_insert_estimator(estimator_name, model_name)
                    rail_svc_utils.safe_insert_estimates(
                        estimates_name,
                        qp_file,
                        estimator_name,
                        dataset_name,
                        n_objects=40000,
                        validate_file=False,
                    )
