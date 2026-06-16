"""Tests for ObjectWrapper: colors, spectrum, redshift, delegation."""

from unittest.mock import MagicMock

import numpy as np
import pytest
import qp

from live_rail.wrappers.object_wrapper import CatalogWrapper, ObjectWrapper


class MockCatalogWrapper(CatalogWrapper):
    """Concrete implementation for testing."""

    def __init__(self, n_objects=10):
        self._n_objects = n_objects
        self._band_names = ["g", "r", "i"]
        self._band_midpoints = np.array([480.0, 620.0, 760.0])
        self._estimate_names = ["est1", "est2"]
        self._wrapped_estimators = {"est1": MagicMock(return_value=MagicMock())}

    def get_nobjects(self):
        return self._n_objects

    def get_band_names(self):
        return self._band_names

    def get_band_midpoints(self):
        return self._band_midpoints

    def get_estimate_names(self):
        return self._estimate_names

    def get_wrapped_estimators(self):
        return self._wrapped_estimators

    def get_data(self, row):
        mags = np.array([22.5, 21.8, 21.2])
        mag_errs = np.array([0.05, 0.03, 0.02])
        estimates = {"est1": MagicMock(spec=qp.Ensemble)}
        true_z = 0.75
        input_data = {"mag_g": np.array([22.5]), "redshift": np.array([0.75])}
        return mags, mag_errs, estimates, true_z, input_data


class TestObjectWrapperInit:
    def test_unpacks_get_data(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        assert obj._magnitudes is not None
        assert obj._magnitude_errors is not None
        assert obj._redshift_estimates is not None
        assert obj._true_redshift == 0.75


class TestObjectWrapperMagnitudes:
    def test_get_magnitudes(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        mags = obj.get_magnitudes()
        assert isinstance(mags, np.ndarray)
        assert len(mags) == 3
        assert mags[0] == 22.5

    def test_get_magnitude_errors(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        errs = obj.get_magnitude_errors()
        assert len(errs) == 3
        assert errs[0] == 0.05


class TestObjectWrapperDelegation:
    def test_get_band_names_from_parent(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        assert obj.get_band_names() == ["g", "r", "i"]

    def test_get_band_midpoints_from_parent(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        midpoints = obj.get_band_midpoints()
        np.testing.assert_array_equal(midpoints, [480.0, 620.0, 760.0])

    def test_get_estimate_names_from_parent(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        assert obj.get_estimate_names() == ["est1", "est2"]

    def test_get_wrapped_estimators_from_parent(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        estimators = obj.get_wrapped_estimators()
        assert "est1" in estimators


class TestObjectWrapperColors:
    def test_returns_dict_of_adjacent_pairs(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        colors = obj.get_colors()
        assert len(colors) == 2
        assert "g - r" in colors
        assert "r - i" in colors

    def test_color_value_is_magnitude_difference(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        colors = obj.get_colors()
        val, err = colors["g - r"]
        assert pytest.approx(val, abs=0.01) == 22.5 - 21.8

    def test_color_error_propagation(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        colors = obj.get_colors()
        val, err = colors["g - r"]
        expected_err = np.sqrt(0.05 + 0.03)
        assert pytest.approx(err, abs=0.01) == expected_err


class TestObjectWrapperSpectrum:
    def test_returns_dict_with_keys(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        spec = obj.get_spectrum()
        assert "midpoints" in spec
        assert "mags" in spec
        assert "mag_errors" in spec

    def test_midpoints_from_parent(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        spec = obj.get_spectrum()
        np.testing.assert_array_equal(spec["midpoints"], [480.0, 620.0, 760.0])

    def test_mags_are_object_magnitudes(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        spec = obj.get_spectrum()
        np.testing.assert_array_equal(spec["mags"], [22.5, 21.8, 21.2])


class TestObjectWrapperRedshift:
    def test_get_redshift_estimates(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        estimates = obj.get_redshift_estimates()
        assert "est1" in estimates

    def test_get_true_redshift(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        assert obj.get_true_redshift() == pytest.approx(0.75)

    def test_get_true_redshift_none(self):
        parent = MockCatalogWrapper()
        parent.get_data = lambda row: (
            np.array([22.5, 21.8, 21.2]),
            np.array([0.05, 0.03, 0.02]),
            {},
            None,
            {},
        )
        obj = ObjectWrapper(parent, 0)
        assert obj.get_true_redshift() is None


class TestObjectWrapperEstimateRedshift:
    def test_calls_wrapped_estimator(self):
        parent = MockCatalogWrapper()
        obj = ObjectWrapper(parent, 0)
        obj.estimate_redshift("est1")
        parent._wrapped_estimators["est1"].assert_called_once()
