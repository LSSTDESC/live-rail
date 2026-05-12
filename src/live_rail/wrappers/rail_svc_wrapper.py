from abc import ABC, abstractmethod 

import numpy as np
import qp

from rail_svc import local_sync, models

from .object_wrapper import ObjectWrapper



    
class RailSvcCatalogWrapper:

    @staticmethod
    def calc_midpoint(band: models.Band) -> float:
        cumul = np.cumsum(band.band_transmission) / np.sum(band.band_transmission)
        mask = cumul > 0.5
        return band.band_wavelengths[np.argmax(mask)]    
    
    def __init__(self, dataset_id: int) -> None:
        self._dataset, self._estimates = local_sync.funcs.get_dataset_and_estimates(dataset_id)
        self._catalog_tag = local_sync.catalog_tag.get_row(self._dataset.catalog_tag_id)        
        self._catalog_band_assocs = local_sync.catalog_band_assoc.find_by(catalog_tag_id=self._dataset.catalog_tag_id)
        self._bands = [local_sync.band.get_row(catalog_band_assoc_.band_id) for catalog_band_assoc_ in self._catalog_band_assocs]
        self._band_names = [band_.name for band_ in self._bands]
        self._band_midpoints = np.array([self.calc_midpoint(band_) for band_ in self._bands])
        self._estimate_names = [estimate_.name for estimate_ in self._estimates]
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

    def get_data(self, row: int) -> tuple[np.ndarray, np.ndarray, dict[str, qp.Ensemble], float|None]:
        input_data, estimates = local_sync.funcs.get_data_and_estimates_data(self._dataset.id_, row)
        mag_vals = np.vstack([input_data[self._mag_column_map.get(band_name_)] for band_name_ in self._band_names])
        mag_err_vals = np.vstack([input_data[self._mag_err_column_map.get(band_name_)] for band_name_ in self._band_names])
        try:
            true_redshift = input_data['redshift']
        except:
            true_redshfit = np.nan

        return np.squeeze(mag_vals), np.squeeze(mag_err_vals), estimates, true_redshift
        
    


    
