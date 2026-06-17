from typing import Callable

import numpy as np
import qp
from rail_svc import local_sync, models, remote_sync

from .object_wrapper import CatalogWrapper, MultiCatalogWrapper, ObjectWrapper


class RailSvcLocalCatalogWrapper(CatalogWrapper):
    @staticmethod
    def calc_midpoint(band: models.Band) -> float:
        cumul = np.cumsum(band.band_transmission) / np.sum(band.band_transmission)
        mask = cumul > 0.5
        return band.band_wavelengths[np.argmax(mask)]

    def __init__(self, dataset_id: int) -> None:
        self._dataset, self._estimates = local_sync.funcs.get_dataset_and_estimates(dataset_id)
        self._catalog_tag = local_sync.catalog_tag.get_row(self._dataset.catalog_tag_id)
        self._catalog_band_assocs = local_sync.catalog_band_assoc.find_by(
            catalog_tag_id=self._dataset.catalog_tag_id
        )
        self._bands = [
            local_sync.band.get_row(catalog_band_assoc_.band_id)
            for catalog_band_assoc_ in self._catalog_band_assocs
        ]
        self._band_names = [band_.name for band_ in self._bands]
        self._band_midpoints = np.array([self.calc_midpoint(band_) for band_ in self._bands])
        self._estimate_names = [estimate_.name for estimate_ in self._estimates]
        the_wrapped_estimators = local_sync.funcs.build_cat_estimator_pdf_wrappers_for_dataset(dataset_id)
        self._wrapped_estimators = {
            wrapper_estimator.estim_name: wrapper_estimator for wrapper_estimator in the_wrapped_estimators
        }
        self._mag_column_map = {}
        self._mag_err_column_map = {}
        for assoc_ in self._catalog_band_assocs:
            assoc_band = local_sync.band.get_row(assoc_.band_id)
            self._mag_column_map[assoc_band.name] = assoc_.mag_column_name
            self._mag_err_column_map[assoc_band.name] = assoc_.mag_err_column_name

    def get_object(self, row: int) -> ObjectWrapper:
        return ObjectWrapper(self, row)

    def get_nobjects(self) -> int:
        return self._dataset.n_objects

    def get_band_names(self) -> list[str]:
        return self._band_names

    def get_band_midpoints(self) -> np.ndarray:
        return self._band_midpoints

    def get_estimate_names(self) -> list[str]:
        return self._estimate_names

    def get_wrapped_estimators(self) -> dict[str, Callable]:
        return self._wrapped_estimators

    def get_data(
        self, row: int
    ) -> tuple[np.ndarray, np.ndarray, dict[str, qp.Ensemble], float | None, dict[str, np.ndarray]]:
        input_data, estimates = local_sync.funcs.get_data_and_estimates_data(self._dataset.id_, row)
        mag_vals = np.array(
            [input_data[self._mag_column_map.get(band_name_)][row] for band_name_ in self._band_names]
        )
        mag_err_vals = np.array(
            [input_data[self._mag_err_column_map.get(band_name_)][row] for band_name_ in self._band_names]
        )

        try:
            true_redshift = float(input_data["redshift"][row])
        except Exception:
            true_redshift = np.nan

        return mag_vals, mag_err_vals, estimates, true_redshift, input_data


class RailSvcLocalSimpleMultiCatalogWrapper(RailSvcLocalCatalogWrapper, MultiCatalogWrapper):
    def __init__(self, dataset_id: int) -> None:

        matched_wrapper = RailSvcLocalCatalogWrapper(dataset_id)
        matched_dataset = matched_wrapper._dataset
        dataset_assocs = local_sync.dataset_assoc.find_by(matched_dataset_id=matched_dataset.id_)
        component_wrappers: dict[str, CatalogWrapper] = {}
        for dataset_assoc_ in dataset_assocs:
            component_dataset = local_sync.dataset.get_row(dataset_assoc_.component_dataset_id)
            component_wrappers[component_dataset.name] = RailSvcLocalCatalogWrapper(component_dataset.id_)
        MultiCatalogWrapper.__init__(self, matched_wrapper, component_wrappers)
        RailSvcLocalCatalogWrapper.__init__(self, dataset_id)

    def get_indices(self, idx: int) -> dict[str, int]:
        return {key: idx for key in self._catalogs.keys()}


class RailSvcRemoteCatalogWrapper(CatalogWrapper):
    @staticmethod
    def calc_midpoint(band: models.Band) -> float:
        cumul = np.cumsum(band.band_transmission) / np.sum(band.band_transmission)
        mask = cumul > 0.5
        return band.band_wavelengths[np.argmax(mask)]

    def __init__(self, dataset_id: int) -> None:
        self._dataset, self._estimates = remote_sync.funcs.get_dataset_and_estimates(dataset_id)
        self._catalog_tag = remote_sync.catalog_tag().get_row(self._dataset.catalog_tag_id)
        self._catalog_band_assocs = remote_sync.catalog_band_assoc().find_by(
            catalog_tag_id=self._dataset.catalog_tag_id
        )
        self._bands = [
            remote_sync.band().get_row(catalog_band_assoc_.band_id)
            for catalog_band_assoc_ in self._catalog_band_assocs
        ]
        self._band_names = [band_.name for band_ in self._bands]
        self._band_midpoints = np.array([self.calc_midpoint(band_) for band_ in self._bands])
        self._estimate_names = [estimate_.name for estimate_ in self._estimates]
        the_wrapped_estimators = remote_sync.funcs.build_cat_estimator_pdf_wrappers_for_dataset(dataset_id)
        self._wrapped_estimators = {
            wrapper_estimator.estim_name: wrapper_estimator for wrapper_estimator in the_wrapped_estimators
        }
        self._mag_column_map = {}
        self._mag_err_column_map = {}
        for assoc_ in self._catalog_band_assocs:
            assoc_band = remote_sync.band().get_row(assoc_.band_id)
            self._mag_column_map[assoc_band.name] = assoc_.mag_column_name
            self._mag_err_column_map[assoc_band.name] = assoc_.mag_err_column_name

    def get_object(self, row: int) -> ObjectWrapper:
        return ObjectWrapper(self, row)

    def get_nobjects(self) -> int:
        return self._dataset.n_objects

    def get_band_names(self) -> list[str]:
        return self._band_names

    def get_band_midpoints(self) -> np.ndarray:
        return self._band_midpoints

    def get_estimate_names(self) -> list[str]:
        return self._estimate_names

    def get_wrapped_estimators(self) -> dict[str, Callable]:
        return self._wrapped_estimators

    def get_data(
        self, row: int
    ) -> tuple[np.ndarray, np.ndarray, dict[str, qp.Ensemble], float | None, dict[str, np.ndarray]]:
        input_data, estimates = remote_sync.funcs.get_data_and_estimates_data(self._dataset.id_, row)
        mag_vals = np.array(
            [input_data[self._mag_column_map.get(band_name_)][row] for band_name_ in self._band_names]
        )
        mag_err_vals = np.array(
            [input_data[self._mag_err_column_map.get(band_name_)][row] for band_name_ in self._band_names]
        )

        try:
            true_redshift = float(input_data["redshift"][row])
        except Exception:
            true_redshift = np.nan

        return mag_vals, mag_err_vals, estimates, true_redshift, input_data


class RailSvcRemoteSimpleMultiCatalogWrapper(RailSvcLocalCatalogWrapper, MultiCatalogWrapper):
    def __init__(self, dataset_id: int) -> None:

        matched_wrapper = RailSvcRemoteCatalogWrapper(dataset_id)
        matched_dataset = matched_wrapper._dataset
        dataset_assocs = remote_sync.dataset_assoc().find_by(matched_dataset_id=matched_dataset.id_)
        component_wrappers: dict[str, CatalogWrapper] = {}
        for dataset_assoc_ in dataset_assocs:
            component_dataset = remote_sync.dataset().get_row(dataset_assoc_.component_dataset_id)
            component_wrappers[component_dataset.name] = RailSvcRemoteCatalogWrapper(component_dataset.id_)
        MultiCatalogWrapper.__init__(self, matched_wrapper, component_wrappers)
        RailSvcRemoteCatalogWrapper.__init__(self, dataset_id)  # type: ignore[arg-type]

    def get_indices(self, idx: int) -> dict[str, int]:
        return {key: idx for key in self._catalogs.keys()}
