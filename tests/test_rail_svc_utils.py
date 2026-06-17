"""Tests for rail_svc_utils safe insert functions."""

from unittest.mock import MagicMock, patch

from live_rail.rail_svc_utils import (
    safe_insert_algo,
    safe_insert_catalog_tag,
    safe_insert_dataset,
    safe_insert_estimates,
    safe_insert_estimator,
    safe_insert_matched_dataset,
    safe_insert_model,
)


class TestSafeInsertFunctions:
    """Test the safe_insert_* pattern used in rail_svc_utils."""

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_algo_creates_when_not_found(self, mock_ls):

        mock_ls.algorithm.get_row_by_name.side_effect = Exception("Not found")
        safe_insert_algo("knn", "rail.knn.KNN")
        mock_ls.algorithm.create_row.assert_called_once_with(name="knn", class_name="rail.knn.KNN")

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_algo_skips_when_exists(self, mock_ls):

        mock_ls.algorithm.get_row_by_name.return_value = MagicMock()
        safe_insert_algo("knn", "rail.knn.KNN")
        mock_ls.algorithm.create_row.assert_not_called()

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_model_creates_when_not_found(self, mock_ls):

        mock_ls.model.get_row_by_name.side_effect = Exception("Not found")
        safe_insert_model("my_model", "/path/model.pkl", "knn", "rubin")
        mock_ls.model.create_row.assert_called_once_with(
            name="my_model", path="/path/model.pkl", algo_name="knn", catalog_tag_name="rubin"
        )

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_estimator_creates_when_not_found(self, mock_ls):

        mock_ls.estimator.get_row_by_name.side_effect = Exception("Not found")
        safe_insert_estimator("est1", "model1", key="value")
        mock_ls.estimator.create_row.assert_called_once_with(
            name="est1", model_name="model1", config={"key": "value"}
        )

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_estimates_creates_when_not_found(self, mock_ls):

        mock_ls.estimates.get_row_by_name.side_effect = Exception("Not found")
        safe_insert_estimates("output1", "/path/out.hdf5", "est1", "ds1", n_objects=100)
        mock_ls.estimates.create_row.assert_called_once_with(
            name="output1", path="/path/out.hdf5", estimator_name="est1", dataset_name="ds1", n_objects=100
        )

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_matched_dataset_creates_when_not_found(self, mock_ls):

        mock_ls.dataset.get_row_by_name.side_effect = Exception("Not found")
        safe_insert_matched_dataset("matched_ds", "rubin", ["comp1", "comp2"], "/path/matched.hdf5", 1000)
        mock_ls.funcs.create_matched_dataset.assert_called_once()

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_catalog_tag_creates_when_not_found(self, mock_ls):

        mock_ls.catalog_tag.get_row_by_name.side_effect = Exception("Not found")
        safe_insert_catalog_tag("lsst")
        mock_ls.catalog_tag.create_row.assert_called_once_with(name="lsst")

    @patch("live_rail.rail_svc_utils.local_sync")
    def test_safe_insert_dataset_creates_when_not_found(self, mock_ls):

        mock_ls.dataset.get_row_by_name.side_effect = Exception("Not found")
        safe_insert_dataset("ds1", "/path/data.hdf5", "rubin", n_objects=500)
        mock_ls.dataset.create_row.assert_called_once_with(
            name="ds1", path="/path/data.hdf5", catalog_tag_name="rubin", n_objects=500
        )
