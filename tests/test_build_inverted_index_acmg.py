import pickle
import json
import pytest
from unittest.mock import patch, MagicMock
from scripts.build_inverted_index_acmg import (
    _normalize_classification,
    _save_metadata,
    build_inverted_index_acmg,
)


class TestNormalizeClassification:
    def test_pathogenic_variants(self):
        assert _normalize_classification("Pathogenic") == "pathogenic"
        assert _normalize_classification("LikelyPathogenic") == "pathogenic"

    def test_benign_variants(self):
        assert _normalize_classification("Benign") == "benign"
        assert _normalize_classification("LikelyBenign") == "likely_benign"

    def test_unknown_classification(self):
        assert _normalize_classification("VUS") is None
        assert _normalize_classification("Unknown") is None
        assert _normalize_classification("") is None
        assert _normalize_classification(None) is None

    def test_case_sensitive_and_exact_match(self):
        assert _normalize_classification("pathogenic") is None
        assert _normalize_classification("Pathogenic ") is None


@patch("scripts.build_inverted_index_acmg.json.dump")
@patch("scripts.build_inverted_index_acmg.open")
def test_save_metadata(mock_open, mock_json_dump, tmp_path):
    with patch("scripts.build_inverted_index_acmg.BASE_DIR", tmp_path):
        _save_metadata(total_rules=42)

    mock_open.assert_called_once()
    args, kwargs = mock_open.call_args
    assert "metadata.json" in str(args[0])
    assert args[1] == "w"

    mock_json_dump.assert_called_once()
    dumped_data = mock_json_dump.call_args[0][0]
    
    assert dumped_data["index_type"] == "acmg_inverted_index"
    assert dumped_data["total_rules"] == 42
    assert set(dumped_data["classification_groups"]) == {
        "pathogenic", "benign", "likely_benign"
    }


@pytest.fixture
def mock_variant():
    variant = MagicMock()
    variant.id = 123
    variant.rules = '[{"name": "PM2", "assessment": "MET"}]'
    variant.classification = "Pathogenic" 
    return variant


@patch("scripts.build_inverted_index_acmg._save_metadata")
@patch("scripts.build_inverted_index_acmg.pickle.dump")
@patch("scripts.build_inverted_index_acmg.open")
@patch("scripts.build_inverted_index_acmg.SessionLocal")
@patch("scripts.build_inverted_index_acmg.extract_met_rules")
def test_build_index_happy_path(
    mock_extract, mock_session, mock_open, mock_pickle, mock_save_meta,
    mock_variant, tmp_path
):
    mock_extract.return_value = ["PM2", "PVS1"]
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    db_mock.query.return_value.yield_per.return_value = [mock_variant]
    
    index_file = tmp_path / "test_index.pkl"
    with patch("scripts.build_inverted_index_acmg.INDEX_PATH", index_file):
        build_inverted_index_acmg()

    db_mock.query.assert_called_once()
    db_mock.close.assert_called_once()
    mock_extract.assert_called_once_with(mock_variant.rules)
    
    mock_pickle.assert_called_once()
    dumped_index = mock_pickle.call_args[0][0]
    
    assert "PM2" in dumped_index
    assert "PVS1" in dumped_index
    assert dumped_index["PM2"]["pathogenic"] == [123]
    assert dumped_index["PVS1"]["pathogenic"] == [123]
    
    mock_save_meta.assert_called_once_with(2)


@patch("scripts.build_inverted_index_acmg._save_metadata")
@patch("scripts.build_inverted_index_acmg.pickle.dump")
@patch("scripts.build_inverted_index_acmg.open")
@patch("scripts.build_inverted_index_acmg.SessionLocal")
@patch("scripts.build_inverted_index_acmg.extract_met_rules")
def test_build_index_skips_invalid_classification(
    mock_extract, mock_session, mock_open, mock_pickle, mock_save_meta,
    tmp_path
):
    variant = MagicMock()
    variant.id = 999
    variant.rules = '[{"name": "PM2", "assessment": "MET"}]'
    variant.classification = "VUS"  
    
    mock_extract.return_value = ["PM2"]
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    db_mock.query.return_value.yield_per.return_value = [variant]
    
    index_file = tmp_path / "test_index.pkl"
    with patch("scripts.build_inverted_index_acmg.INDEX_PATH", index_file):
        build_inverted_index_acmg()

    dumped_index = mock_pickle.call_args[0][0]
    assert dumped_index == {}
    mock_save_meta.assert_called_once_with(0)


@patch("scripts.build_inverted_index_acmg._save_metadata")
@patch("scripts.build_inverted_index_acmg.pickle.dump")
@patch("scripts.build_inverted_index_acmg.open")
@patch("scripts.build_inverted_index_acmg.SessionLocal")
@patch("scripts.build_inverted_index_acmg.extract_met_rules")
def test_build_index_empty_rules(
    mock_extract, mock_session, mock_open, mock_pickle, mock_save_meta,
    tmp_path
):
    variant = MagicMock()
    variant.id = 42
    variant.rules = "[]"
    variant.classification = "Benign"
    
    mock_extract.return_value = []
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    db_mock.query.return_value.yield_per.return_value = [variant]
    
    index_file = tmp_path / "test_index.pkl"
    with patch("scripts.build_inverted_index_acmg.INDEX_PATH", index_file):
        build_inverted_index_acmg()

    dumped_index = mock_pickle.call_args[0][0]
    assert dumped_index == {}


@patch("scripts.build_inverted_index_acmg._save_metadata")
@patch("scripts.build_inverted_index_acmg.pickle.dump")
@patch("scripts.build_inverted_index_acmg.open")
@patch("scripts.build_inverted_index_acmg.SessionLocal")
@patch("scripts.build_inverted_index_acmg.extract_met_rules")
def test_build_index_sorts_postings(
    mock_extract, mock_session, mock_open, mock_pickle, mock_save_meta,
    tmp_path
):
    variants = []
    for vid in [300, 100, 200]:
        v = MagicMock()
        v.id = vid
        v.rules = '[{"name": "PM2", "assessment": "MET"}]'
        v.classification = "Pathogenic"
        variants.append(v)
    
    mock_extract.return_value = ["PM2"]
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    db_mock.query.return_value.yield_per.return_value = variants
    
    index_file = tmp_path / "test_index.pkl"
    with patch("scripts.build_inverted_index_acmg.INDEX_PATH", index_file):
        build_inverted_index_acmg()

    dumped_index = mock_pickle.call_args[0][0]
    assert dumped_index["PM2"]["pathogenic"] == [100, 200, 300]


@patch("scripts.build_inverted_index_acmg._save_metadata")
@patch("scripts.build_inverted_index_acmg.pickle.dump")
@patch("scripts.build_inverted_index_acmg.open")
@patch("scripts.build_inverted_index_acmg.SessionLocal")
@patch("scripts.build_inverted_index_acmg.extract_met_rules")
def test_build_index_multiple_classifications_per_rule(
    mock_extract, mock_session, mock_open, mock_pickle, mock_save_meta,
    tmp_path
):
    variants = [
        MagicMock(id=1, rules='[{"name": "PM2", "assessment": "MET"}]', classification="Pathogenic"),
        MagicMock(id=2, rules='[{"name": "PM2", "assessment": "MET"}]', classification="Benign"),
        MagicMock(id=3, rules='[{"name": "PM2", "assessment": "MET"}]', classification="LikelyBenign"),
    ]
    
    mock_extract.return_value = ["PM2"]
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    db_mock.query.return_value.yield_per.return_value = variants
    
    index_file = tmp_path / "test_index.pkl"
    with patch("scripts.build_inverted_index_acmg.INDEX_PATH", index_file):
        build_inverted_index_acmg()

    dumped_index = mock_pickle.call_args[0][0]
    
    assert dumped_index["PM2"]["pathogenic"] == [1]
    assert dumped_index["PM2"]["benign"] == [2]
    assert dumped_index["PM2"]["likely_benign"] == [3]


@patch("scripts.build_inverted_index_acmg._save_metadata")
@patch("scripts.build_inverted_index_acmg.pickle.dump")
@patch("scripts.build_inverted_index_acmg.open")
@patch("scripts.build_inverted_index_acmg.SessionLocal")
def test_build_index_empty_database(
    mock_session, mock_open, mock_pickle, mock_save_meta,
    tmp_path
):
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    db_mock.query.return_value.yield_per.return_value = []
    
    index_file = tmp_path / "test_index.pkl"
    with patch("scripts.build_inverted_index_acmg.INDEX_PATH", index_file):
        build_inverted_index_acmg()

    dumped_index = mock_pickle.call_args[0][0]
    assert dumped_index == {}
    mock_save_meta.assert_called_once_with(0)


@patch("scripts.build_inverted_index_acmg._save_metadata")
@patch("scripts.build_inverted_index_acmg.pickle.dump")
@patch("scripts.build_inverted_index_acmg.open")
@patch("scripts.build_inverted_index_acmg.SessionLocal")
@patch("scripts.build_inverted_index_acmg.extract_met_rules")
def test_build_index_duplicate_rules_in_variant(
    mock_extract, mock_session, mock_open, mock_pickle, mock_save_meta,
    tmp_path
):
    variant = MagicMock()
    variant.id = 777
    variant.rules = '[{"name": "PM2", "assessment": "MET"}, {"name": "PM2", "assessment": "MET"}]'
    variant.classification = "Pathogenic"
    
    mock_extract.return_value = ["PM2"]
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    db_mock.query.return_value.yield_per.return_value = [variant]
    
    index_file = tmp_path / "test_index.pkl"
    with patch("scripts.build_inverted_index_acmg.INDEX_PATH", index_file):
        build_inverted_index_acmg()

    dumped_index = mock_pickle.call_args[0][0]
    assert dumped_index["PM2"]["pathogenic"] == [777]
    assert len(dumped_index["PM2"]["pathogenic"]) == 1