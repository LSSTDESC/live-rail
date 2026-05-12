from __future__ import annotations

from abc import ABC, abstractmethod 
import numpy as np
import qp


class ObjectWrapper:
    
    @staticmethod
    def _get_mode(
        ensemble: qp.Ensemble,
    ) -> float:
        try:
            return float(np.squeeze(ensemble.ancil['zmode']))
        except:
            return 0.

    @staticmethod
    def _get_rms(
        ensemble: qp.Ensemble,
    ) -> float:
        try:
            return float(np.squeeze(ensemble.ancil['rms']))
        except:
            return 0.

    def __init__(self, parent: CatalogWrapper, row: int):
        self._parent = parent
        self._magnitudes, self._magnitude_errors, self._redshift_estimates, self._true_redshift = self._parent.get_data(row)
        
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
        return self._true_redshift        

    def get_redshift_modes(self) ->dict[str, float]:
        all_pdfs = self.get_redshift_estimates()
        return {k:self._get_mode(v) for k, v in all_pdfs.items()}

    def get_redshift_rms_vals(self) ->dict[str, float]:
        all_pdfs = self.get_redshift_estimates()
        return {k:self._get_rms(v) for k, v in all_pdfs.items()}

    def get_redshifts_pdfs(self, grid: np.ndarray) -> dict[str, np.ndarray]:
        all_pdfs = self.get_redshift_estimates()
        return {k:np.squeeze(v.pdf(grid)) for k, v in all_pdfs.items()}
        
    def get_colors(self) -> dict[str, tuple[float, float]]:
        ret_dict: str = {}
        band_names = self.get_band_names()
        mags = self.get_magnitudes()
        mag_errors = self.get_magnitude_errors()        
        n = len(band_names)
        for i in range(n-1):
            color_name = f"{band_names[i]} - {band_names[i+1]}"
            ret_dict[color_name] = (mags[i] - mags[i+1], np.sqrt(mag_errors[i] + mag_errors[i+1]))
        return ret_dict
    
    def get_spectrum(self) -> dict[str, np.ndarray]:
        ret_dict = dict(
            midpoints=self.get_band_midpoints(),
            mags=self.get_magnitudes(),
            mag_errors=self.get_magnitude_errors(),
        )
        return ret_dict
        
    
class CatalogWrapper(ABC):

    def get_object(self, idx: int) -> ObjectWrapper:
        return ObjectWrapper(self, int)
    
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
    def get_data(self, row: int) -> tuple[np.ndarry, np.ndarray, dict[str, qp.Ensemble], float|None]:
        pass
