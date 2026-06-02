import os
import pprint
from typing import Any
from pathlib import Path
import yaml

import click

import tables_io
import qp

from rail.utils import catalog_utils
from rail.estimation.algos import bpz_lite

from live_rail.wrappers.cat_estimator_pdf_wrapper import CatEstimatorPdfWrapper
from live_rail.apps.cat_pdf_app import build_cat_pdf_app
from live_rail.apps.cat_pdf_cloud_app import build_cat_pdf_cloud_app
from live_rail.apps.cat_data_app import build_data_app
from live_rail.apps.cat_multi_data_app import build_multi_data_app

from . import options

from live_rail._version import __version__


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """Live RAIL server"""


@cli.command(name="view-data")
@options.port()
@options.data_path()
@options.pz_estimate_path()
@options.debug()
def view_data(
    port: int,
    data_path: Path,
    pz_estimate_path: Path,
    debug: bool,    
) -> int:
    """View data"""
    cat_data = tables_io.read(data_path)
    pz_data = qp.read(pz_estimate_path)
    app = build_data_app(cat_data, pz_data)
    app.run(debug=debug, port=port)
    return 0


@cli.command(name="view-multi-data")
@options.port()
@options.data_path()
@options.pz_estimates_yaml()
@options.debug()
def view_multi_data(
    port: int,
    data_path: Path,
    pz_estimates_yaml: Path,
    debug: bool,    
) -> int:
    """View data"""
    cat_data = tables_io.read(data_path)
    with open(pz_estimates_yaml) as fin:
        yaml_dict = yaml.safe_load(fin)
    pz_data = {k: qp.read(v) for k, v in yaml_dict.items()}
    app = build_multi_data_app(cat_data, pz_data)
    app.run(debug=debug, port=port)
    return 0



@cli.command(name="pdf-family")
@options.port()
@options.debug()
def pdf_family(
    port: int,
    debug: bool,
) -> int:
    """View PDFs near a point"""
    model_file = 'nb/pz_challenge_taskset_1_cardinal_pz_model_10yr.pkl'

    catalog_utils.load_yaml("nb/catalogs.yaml")
    catalog_utils.apply("cardinal_roman_rubin")

    wrapper = CatEstimatorPdfWrapper.build_nobj_wrapper(
        bpz_lite.BPZliteEstimator,
        n_obj=20,
        name="estimate",
        model=model_file,
        output_mode="return",
        spectra_file="COSMOS_seds.list",
    )
    
    app = build_cat_pdf_cloud_app(wrapper)
    app.run(debug=debug, port=port)
    return 0


@cli.command(name="pdf")
@options.port()
@options.debug()
def pdf(
    port: int,
    debug: bool,
) -> int:
    """View PDFs at a point"""
    model_file = 'nb/pz_challenge_taskset_1_cardinal_pz_model_10yr.pkl'

    catalog_utils.load_yaml("nb/catalogs.yaml")
    catalog_utils.apply("cardinal_roman_rubin")

    wrapper = CatEstimatorPdfWrapper.build_wrapper(
        bpz_lite.BPZliteEstimator,
        name="estimate",
        model=model_file,
        output_mode="return",
        spectra_file="COSMOS_seds.list",
    )
    
    app = build_cat_pdf_app(wrapper)
    app.run(debug=debug, port=port)
    return 0

