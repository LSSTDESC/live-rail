from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np
import qp


class ObjectWrapper:
    @staticmethod
    def build_catalog_samples(
        inputs_data: dict[str, np.ndarray],
        band_names: list[str],
        mag_column_map: dict[str, str],
        mag_err_column_map: dict[str, str],
        mag_err_scale: float = 1,
        n_samples: int = 20,
    ) -> dict[str, np.ndarray]:
        out_dict: dict[str, np.ndarray] = {}
        for band in band_names:
            mag_name = mag_column_map[band]
            mag_err_name = mag_err_column_map[band]
            mag = inputs_data[mag_name]
            mag_err = inputs_data[mag_err_name]
            out_dict[mag_name] = np.random.normal(
                loc=mag,
                scale=mag_err_scale * mag_err,
                size=n_samples,
            )
            out_dict[mag_err_name] = np.ones(n_samples) * mag_err
        return out_dict

    @staticmethod
    def _get_mode(
        ensemble: qp.Ensemble,
    ) -> float:
        try:
            return float(np.squeeze(ensemble.ancil["zmode"]))
        except (KeyError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _get_rms(
        ensemble: qp.Ensemble,
    ) -> float:
        try:
            return float(np.squeeze(ensemble.ancil["rms"]))
        except (KeyError, TypeError, ValueError):
            return 0.0

    def __init__(self, parent: CatalogWrapper, row: int):
        self._parent = parent
        (
            self._magnitudes,
            self._magnitude_errors,
            self._redshift_estimates,
            self._true_redshift,
            self._input_data,
        ) = self._parent.get_data(row)

    def get_band_names(self) -> list[str]:
        return self._parent.get_band_names()

    def get_estimate_names(self) -> list[str]:
        return self._parent.get_estimate_names()

    def get_magnitudes(self) -> np.ndarray:
        return self._magnitudes

    def get_magnitude_errors(self) -> np.ndarray:
        return self._magnitude_errors

    def get_band_midpoints(self) -> np.ndarray:
        return self._parent.get_band_midpoints()

    def get_redshift_estimates(self) -> dict[str, qp.Ensemble]:
        return self._redshift_estimates

    def get_redshift_estimate(self, estimate_name: str) -> qp.Ensemble:
        return self._redshift_estimates[estimate_name]

    def get_true_redshift(self) -> float | None:
        if self._true_redshift is None:
            return None
        return float(np.squeeze(self._true_redshift))

    def get_redshift_modes(self) -> dict[str, float]:
        all_pdfs = self.get_redshift_estimates()
        return {k: self._get_mode(v) for k, v in all_pdfs.items()}

    def get_redshift_rms_vals(self) -> dict[str, float]:
        all_pdfs = self.get_redshift_estimates()
        return {k: self._get_rms(v) for k, v in all_pdfs.items()}

    def get_redshifts_pdfs(self, grid: np.ndarray) -> dict[str, np.ndarray]:
        all_pdfs = self.get_redshift_estimates()
        return {k: np.squeeze(v.pdf(grid)) for k, v in all_pdfs.items()}

    def get_colors(self) -> dict[str, tuple[float, float]]:
        ret_dict: dict[str, tuple[float, float]] = {}
        band_names = self.get_band_names()
        mags = self.get_magnitudes()
        mag_errors = self.get_magnitude_errors()
        n = len(band_names)
        for i in range(n - 1):
            color_name = f"{band_names[i]} - {band_names[i + 1]}"
            ret_dict[color_name] = (mags[i] - mags[i + 1], np.sqrt(mag_errors[i] + mag_errors[i + 1]))
        return ret_dict

    def get_spectrum(self) -> dict[str, np.ndarray]:
        ret_dict = dict(
            midpoints=self.get_band_midpoints(),
            mags=self.get_magnitudes(),
            mag_errors=self.get_magnitude_errors(),
        )
        return ret_dict

    def get_wrapped_estimators(self) -> dict[str, Callable]:
        return self._parent.get_wrapped_estimators()

    def estimate_redshift(self, estimator_name: str) -> qp.Ensemble:
        the_estimator = self._parent.get_wrapped_estimators()[estimator_name]
        return the_estimator(self._input_data)

    def estimate_many_redshifts(self, estimator_name: str, the_data: dict[str, np.ndarray]) -> qp.Ensemble:
        the_estimator = self._parent.get_wrapped_estimators()[estimator_name]
        return the_estimator(the_data)


class MultiObjectWapper(ObjectWrapper):
    def __init__(self, parent: CatalogWrapper, row: int, objects: dict[str, ObjectWrapper]) -> None:
        ObjectWrapper.__init__(self, parent, row)
        self._objects = objects

    @property
    def objects(self) -> dict[str, ObjectWrapper]:
        return self._objects

    def get_objects(self, catalogs: list[str]) -> dict[str, ObjectWrapper]:
        ret_dict: dict[str, ObjectWrapper] = {}
        for key in catalogs:
            any_object = self._objects[key]
            ret_dict[key] = any_object
        return ret_dict


class CatalogWrapper(ABC):
    def get_object(self, idx: int) -> ObjectWrapper:
        return ObjectWrapper(self, idx)

    @abstractmethod
    def get_nobjects(self) -> int:
        pass

    @abstractmethod
    def get_band_names(self) -> list[str]:
        pass

    @abstractmethod
    def get_band_midpoints(self) -> np.ndarray:
        pass

    @abstractmethod
    def get_estimate_names(self) -> list[str]:
        pass

    @abstractmethod
    def get_wrapped_estimators(self) -> dict[str, Callable]:
        pass

    @abstractmethod
    def get_data(
        self, row: int
    ) -> tuple[np.ndarray, np.ndarray, dict[str, qp.Ensemble], float | None, dict[str, np.ndarray]]:
        pass


class MultiCatalogWrapper(CatalogWrapper):
    def __init__(
        self, matched_catalog: CatalogWrapper, component_catalogs: dict[str, CatalogWrapper]
    ) -> None:
        self._matched_catalog = matched_catalog
        self._catalogs = component_catalogs

    @abstractmethod
    def get_indices(self, idx: int) -> dict[str, int]:
        pass

    def get_nobjects(self) -> int:
        return self._matched_catalog.get_nobjects()

    def get_estimates(self, idx: int) -> dict[str, qp.Ensemble]:
        return self._matched_catalog.get_object(idx).get_redshift_estimates()

    def get_estimate_names(self) -> list[str]:
        return self._matched_catalog.get_estimate_names()

    def get_band_names(self) -> list[str]:
        return self._matched_catalog.get_band_names()

    def get_band_midpoints(self) -> np.ndarray:
        return self._matched_catalog.get_band_midpoints()

    def get_component_data(
        self, row: int
    ) -> tuple[np.ndarray, np.ndarray, dict[str, qp.Ensemble], float | None]:
        all_mag_vals: list[np.ndarray] = []
        all_mag_err_vals: list[np.ndarray] = []
        the_true_redshift: float | None = None
        objects = self.get_objects(row)
        all_estimates: dict[str, qp.Ensemble] = {}
        for key, val in objects.items():
            mag_vals = val.get_magnitudes()
            mag_err_vals = val.get_magnitude_errors()
            estimates = val.get_redshift_estimates()
            all_estimates.update(**estimates)
            true_redshift = val.get_true_redshift()
            assert isinstance(mag_vals, np.ndarray)
            assert isinstance(mag_err_vals, np.ndarray)
            all_mag_vals.append(mag_vals)
            all_mag_err_vals.append(mag_err_vals)
            if true_redshift is not None:
                the_true_redshift = true_redshift
        return np.hstack(all_mag_vals), np.hstack(all_mag_err_vals), all_estimates, the_true_redshift

    def get_wrapper(self, idx: int) -> MultiObjectWapper:
        indices = self.get_indices(idx)
        multi_obj_dict: dict[str, ObjectWrapper] = {}
        for key, val in indices.items():
            obj_wrapper = self._catalogs[key].get_object(val)
            multi_obj_dict[key] = obj_wrapper
        return MultiObjectWapper(self, idx, multi_obj_dict)

    def get_objects(self, idx: int) -> dict[str, ObjectWrapper]:
        wrapper = self.get_wrapper(idx)
        return wrapper.get_objects(list(self._catalogs.keys()))

    def get_catalog(self, catalog_name: str) -> CatalogWrapper:
        return self._catalogs[catalog_name]

    def get_catalog_band_names(self) -> dict[str, list[str]]:
        return {key: val.get_band_names() for key, val in self._catalogs.items()}

    def get_catalog_band_midpoints(self) -> dict[str, np.ndarray]:
        return {key: val.get_band_midpoints() for key, val in self._catalogs.items()}

    def get_catalog_estimate_names(self) -> dict[str, list[str]]:
        return {key: val.get_estimate_names() for key, val in self._catalogs.items()}
