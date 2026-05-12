import numpy as np

from rail.utils import catalog_utils
from rail.estimation.estimator import CatEstimator


class CatEstimatorPdfWrapper:
    """Helper class to use a CatEstimator with in memory data
    """    
    def __init__(
        self,
        cat_estimator: CatEstimator,
        names: list[str],
        n_obj: int=1,
    ):
        """Constructor
        
        Parameters
        ----------
        cat_estimator:
            CatEstimator to wrap
            
        point_estimate:
            Which point estimate to use
        """
        self._estimator = cat_estimator
        self._estimator.open_model(**self._estimator.config)
        self._estimator.data_store.clear()
        self._estimator._input_length = n_obj
        self._estimator._initialize_run()
        self._names = names.copy
        self._n_obj = n_obj
        dd = {name_:np.array([1.]) for name_ in names}        
        self._estimator._process_chunk(0, self._n_obj, dd, True)
        

    @property
    def n_obj(self):
        return self._n_obj
        
    def __call__(self, vals: dict[str, np.ndarray]):
        """Evaluation function

        Parameters
        ----------
        vals: 
            Should have shape [N_params, N_values]
            
        Returns
        -------
        np.ndarray[..., N_params, N_values] estimates using different values of parameter
        """
        try:
            self._estimator._process_chunk(0, self._n_obj, vals, False)
        except:
            pass
        estimates = self._estimator._output_handle.data
        return estimates


    @classmethod
    def build_wrapper(
        cls,
        estim_class,
        **kwargs,
    ):
        names = list(catalog_utils.get_active_tag().band_name_dict().values())

        var_names = []
        var_names += names
        var_names += [f"{name_}_err" for name_ in names]

        estimator = estim_class.make_stage(**kwargs)
        wrapper = cls(estimator, var_names)
        return wrapper
        
    @classmethod
    def build_nobj_wrapper(
        cls,
        estim_class,
        n_obj,
        **kwargs,
    ):
        names = list(catalog_utils.get_active_tag().band_name_dict().values())

        var_names = []
        var_names += names
        var_names += [f"{name_}_err" for name_ in names]

        estimator = estim_class.make_stage(**kwargs)
        wrapper = cls(estimator, var_names, n_obj)
        return wrapper
