"""Tests for RailSvcLocalCatalogWrapper and RailSvcRemoteCatalogWrapper."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from live_rail.wrappers.rail_svc_wrapper import RailSvcLocalCatalogWrapper


class TestCalcMidpoint:
    def test_symmetric_transmission(self):
        band = MagicMock()
        band.band_wavelengths = np.array([400.0, 450.0, 500.0, 550.0, 600.0])
        band.band_transmission = np.array([0.0, 0.25, 0.5, 0.25, 0.0])
        midpoint = RailSvcLocalCatalogWrapper.calc_midpoint(band)
        assert 450.0 <= midpoint <= 550.0

    def test_skewed_transmission(self):
        band = MagicMock()
        band.band_wavelengths = np.array([400.0, 500.0, 600.0, 700.0, 800.0])
        band.band_transmission = np.array([0.0, 0.0, 0.0, 0.5, 1.0])
        midpoint = RailSvcLocalCatalogWrapper.calc_midpoint(band)
        assert midpoint >= 700.0


class TestRailSvcLocalCatalogWrapperInit:
    @patch("live_rail.wrappers.rail_svc_wrapper.local_sync")
    def test_calls_get_dataset_and_estimates(self, mock_ls):
        mock_dataset = MagicMock()
        mock_dataset.catalog_tag_id = 1
        mock_dataset.n_objects = 100
        mock_estimates = [MagicMock(name="est1")]
        mock_ls.funcs.get_dataset_and_estimates.return_value = (mock_dataset, mock_estimates)
        mock_ls.catalog_tag.get_row.return_value = MagicMock(name="rubin")
        mock_ls.catalog_band_assoc.find_by.return_value = []
        mock_ls.funcs.build_cat_estimator_pdf_wrappers_for_dataset.return_value = []

        wrapper = RailSvcLocalCatalogWrapper(1)
        mock_ls.funcs.get_dataset_and_estimates.assert_called_once_with(1)
        assert wrapper.get_nobjects() == 100

    @patch("live_rail.wrappers.rail_svc_wrapper.local_sync")
    def test_builds_band_maps(self, mock_ls):
        mock_dataset = MagicMock()
        mock_dataset.catalog_tag_id = 1
        mock_dataset.n_objects = 50

        mock_band = MagicMock()
        mock_band.name = "g_band"
        mock_band.band_wavelengths = np.array([400.0, 500.0, 600.0])
        mock_band.band_transmission = np.array([0.0, 1.0, 0.0])

        mock_assoc = MagicMock()
        mock_assoc.band_id = 1
        mock_assoc.mag_column_name = "mag_g"
        mock_assoc.mag_err_column_name = "mag_g_err"

        mock_ls.funcs.get_dataset_and_estimates.return_value = (mock_dataset, [])
        mock_ls.catalog_tag.get_row.return_value = MagicMock()
        mock_ls.catalog_band_assoc.find_by.return_value = [mock_assoc]
        mock_ls.band.get_row.return_value = mock_band
        mock_ls.funcs.build_cat_estimator_pdf_wrappers_for_dataset.return_value = []

        wrapper = RailSvcLocalCatalogWrapper(1)
        assert wrapper.get_band_names() == ["g_band"]
        assert wrapper._mag_column_map["g_band"] == "mag_g"


class TestRailSvcLocalCatalogWrapperGetData:
    @patch("live_rail.wrappers.rail_svc_wrapper.local_sync")
    def test_indexes_into_row(self, mock_ls):
        mock_dataset = MagicMock()
        mock_dataset.catalog_tag_id = 1
        mock_dataset.n_objects = 10
        mock_dataset.id_ = 1

        mock_band = MagicMock()
        mock_band.name = "g"
        mock_band.band_wavelengths = np.array([500.0])
        mock_band.band_transmission = np.array([1.0])

        mock_assoc = MagicMock()
        mock_assoc.band_id = 1
        mock_assoc.mag_column_name = "mag_g"
        mock_assoc.mag_err_column_name = "mag_g_err"

        mock_ls.funcs.get_dataset_and_estimates.return_value = (mock_dataset, [])
        mock_ls.catalog_tag.get_row.return_value = MagicMock()
        mock_ls.catalog_band_assoc.find_by.return_value = [mock_assoc]
        mock_ls.band.get_row.return_value = mock_band
        mock_ls.funcs.build_cat_estimator_pdf_wrappers_for_dataset.return_value = []

        # get_data_and_estimates_data returns full arrays
        input_data = {
            "mag_g": np.array([22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0]),
            "mag_g_err": np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]),
            "redshift": np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]),
        }
        mock_ls.funcs.get_data_and_estimates_data.return_value = (input_data, {})

        wrapper = RailSvcLocalCatalogWrapper(1)
        mags, errs, estimates, true_z, raw = wrapper.get_data(3)

        assert mags[0] == 25.0  # row 3
        assert errs[0] == 0.4
        assert true_z == pytest.approx(0.4)

    @patch("live_rail.wrappers.rail_svc_wrapper.local_sync")
    def test_handles_missing_redshift(self, mock_ls):
        mock_dataset = MagicMock()
        mock_dataset.catalog_tag_id = 1
        mock_dataset.n_objects = 5
        mock_dataset.id_ = 1

        mock_band = MagicMock()
        mock_band.name = "g"
        mock_band.band_wavelengths = np.array([500.0])
        mock_band.band_transmission = np.array([1.0])

        mock_assoc = MagicMock()
        mock_assoc.band_id = 1
        mock_assoc.mag_column_name = "mag_g"
        mock_assoc.mag_err_column_name = "mag_g_err"

        mock_ls.funcs.get_dataset_and_estimates.return_value = (mock_dataset, [])
        mock_ls.catalog_tag.get_row.return_value = MagicMock()
        mock_ls.catalog_band_assoc.find_by.return_value = [mock_assoc]
        mock_ls.band.get_row.return_value = mock_band
        mock_ls.funcs.build_cat_estimator_pdf_wrappers_for_dataset.return_value = []

        # No redshift column
        input_data = {
            "mag_g": np.array([22.0, 23.0, 24.0, 25.0, 26.0]),
            "mag_g_err": np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
        }
        mock_ls.funcs.get_data_and_estimates_data.return_value = (input_data, {})

        wrapper = RailSvcLocalCatalogWrapper(1)
        mags, errs, estimates, true_z, raw = wrapper.get_data(0)

        assert np.isnan(true_z)
