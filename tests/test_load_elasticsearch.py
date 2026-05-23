import pytest
from unittest.mock import patch, MagicMock, call
from scripts.load_elasticsearch import (
    _recreate_index,
    load_elasticsearch,
    INDEX_NAME,
    ALLOWED_CLASSIFICATIONS,
)

class TestRecreateIndex:
    def test_delete_and_create_when_exists(self):
        es_mock = MagicMock()
        es_mock.indices.exists.return_value = True
        
        _recreate_index(es_mock)

        es_mock.indices.exists.assert_called_once_with(index=INDEX_NAME)
        es_mock.indices.delete.assert_called_once_with(index=INDEX_NAME)
        es_mock.indices.create.assert_called_once()
        args, kwargs = es_mock.indices.create.call_args
        assert kwargs.get("index") == INDEX_NAME
        body = kwargs.get("body")
        assert "mappings" in body
        assert "properties" in body["mappings"]
        assert "rules" in body["mappings"]["properties"]
        assert body["mappings"]["properties"]["rules"]["type"] == "nested"

    def test_skip_delete_when_not_exists(self):
        es_mock = MagicMock()
        es_mock.indices.exists.return_value = False
        
        _recreate_index(es_mock)

        es_mock.indices.exists.assert_called_once_with(index=INDEX_NAME)
        es_mock.indices.delete.assert_not_called()
        es_mock.indices.create.assert_called_once()


@pytest.fixture
def mock_es():
    return MagicMock()

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def mock_variant():
    variant = MagicMock()
    variant.id = 123
    variant.rules = '[{"name": "PM2", "assessment": "MET"}, {"name": "PVS1", "assessment": "MET"}]'
    variant.classification = "Pathogenic"
    variant.gene = "BRCA1"
    variant.chr = "17"
    variant.pos = 43044295
    return variant


@patch("scripts.load_elasticsearch._recreate_index")
@patch("scripts.load_elasticsearch.bulk")
@patch("scripts.load_elasticsearch.Elasticsearch")
@patch("scripts.load_elasticsearch.SessionLocal")
def test_load_es_happy_path(
    mock_session_class, mock_es_class, mock_bulk, mock_recreate,
    mock_es, mock_db_session, mock_variant, tmp_path
):
    mock_session_class.return_value = mock_db_session
    mock_es_class.return_value = mock_es
    mock_db_session.query.return_value.yield_per.return_value = [mock_variant]

    with patch("scripts.load_elasticsearch.INDEX_NAME", "test_index"):
        load_elasticsearch()

    mock_recreate.assert_called_once_with(mock_es)
    mock_db_session.close.assert_called_once()
    
    assert mock_bulk.call_count == 1
    actions = mock_bulk.call_args[0][1]
    assert len(actions) == 1
    
    doc = actions[0]
    assert doc["_index"] == "test_index"
    assert doc["_id"] == 123
    assert doc["_source"]["classification"] == "pathogenic"
    assert doc["_source"]["gene"] == "BRCA1"
    assert doc["_source"]["rules"] == [
        {"name": "PM2", "assessment": "MET"},
        {"name": "PVS1", "assessment": "MET"}
    ]


@patch("scripts.load_elasticsearch._recreate_index")
@patch("scripts.load_elasticsearch.bulk")
@patch("scripts.load_elasticsearch.Elasticsearch")
@patch("scripts.load_elasticsearch.SessionLocal")
def test_load_es_skips_invalid_classification(
    mock_session_class, mock_es_class, mock_bulk, mock_recreate,
    mock_es, mock_db_session, tmp_path
):
    variant = MagicMock()
    variant.id = 999
    variant.rules = '[{"name": "PM2", "assessment": "MET"}]'
    variant.classification = "VUS" 
    
    mock_session_class.return_value = mock_db_session
    mock_es_class.return_value = mock_es
    mock_db_session.query.return_value.yield_per.return_value = [variant]

    with patch("scripts.load_elasticsearch.INDEX_NAME", "test_index"):
        load_elasticsearch()

    mock_bulk.assert_not_called()


@patch("scripts.load_elasticsearch._recreate_index")
@patch("scripts.load_elasticsearch.bulk")
@patch("scripts.load_elasticsearch.Elasticsearch")
@patch("scripts.load_elasticsearch.SessionLocal")
def test_load_es_handles_empty_rules(
    mock_session_class, mock_es_class, mock_bulk, mock_recreate,
    mock_es, mock_db_session, tmp_path
):
    variant = MagicMock()
    variant.id = 42
    variant.rules = None
    variant.classification = "Benign"
    variant.gene = "TP53"
    variant.chr = "17"
    variant.pos = 7577539
    
    mock_session_class.return_value = mock_db_session
    mock_es_class.return_value = mock_es
    mock_db_session.query.return_value.yield_per.return_value = [variant]

    with patch("scripts.load_elasticsearch.INDEX_NAME", "test_index"):
        load_elasticsearch()

    actions = mock_bulk.call_args[0][1]
    assert len(actions) == 1
    assert actions[0]["_source"]["rules"] == []


@patch("scripts.load_elasticsearch._recreate_index")
@patch("scripts.load_elasticsearch.bulk")
@patch("scripts.load_elasticsearch.Elasticsearch")
@patch("scripts.load_elasticsearch.SessionLocal")
def test_load_es_handles_invalid_json_rules(
    mock_session_class, mock_es_class, mock_bulk, mock_recreate,
    mock_es, mock_db_session, tmp_path
):
    variant = MagicMock()
    variant.id = 777
    variant.rules = "not valid json"
    variant.classification = "LikelyBenign"
    variant.gene = "MLH1"
    variant.chr = "3"
    variant.pos = 37043024
    
    mock_session_class.return_value = mock_db_session
    mock_es_class.return_value = mock_es
    mock_db_session.query.return_value.yield_per.return_value = [variant]

    with patch("scripts.load_elasticsearch.INDEX_NAME", "test_index"):
        load_elasticsearch()

    actions = mock_bulk.call_args[0][1]
    assert len(actions) == 1
    assert actions[0]["_source"]["rules"] == []


@patch("scripts.load_elasticsearch._recreate_index")
@patch("scripts.load_elasticsearch.bulk")
@patch("scripts.load_elasticsearch.Elasticsearch")
@patch("scripts.load_elasticsearch.SessionLocal")
def test_load_es_filters_non_met_rules(
    mock_session_class, mock_es_class, mock_bulk, mock_recreate,
    mock_es, mock_db_session, tmp_path
):
    variant = MagicMock()
    variant.id = 555
    variant.rules = '[{"name": "PM2", "assessment": "MET"}, {"name": "PP3", "assessment": "BENIGN"}]'
    variant.classification = "Pathogenic"
    variant.gene = "ATM"
    variant.chr = "11"
    variant.pos = 108098888
    
    mock_session_class.return_value = mock_db_session
    mock_es_class.return_value = mock_es
    mock_db_session.query.return_value.yield_per.return_value = [variant]

    with patch("scripts.load_elasticsearch.INDEX_NAME", "test_index"):
        load_elasticsearch()

    actions = mock_bulk.call_args[0][1]
    assert len(actions) == 1
    assert actions[0]["_source"]["rules"] == [
        {"name": "PM2", "assessment": "MET"}
    ]


@patch("scripts.load_elasticsearch._recreate_index")
@patch("scripts.load_elasticsearch.bulk")
@patch("scripts.load_elasticsearch.Elasticsearch")
@patch("scripts.load_elasticsearch.SessionLocal")
def test_load_es_removes_duplicate_rules(
    mock_session_class, mock_es_class, mock_bulk, mock_recreate,
    mock_es, mock_db_session, tmp_path
):
    variant = MagicMock()
    variant.id = 888
    variant.rules = '[{"name": "PM2", "assessment": "MET"}, {"name": "PM2", "assessment": "MET"}]'
    variant.classification = "Benign"
    variant.gene = "CHEK2"
    variant.chr = "22"
    variant.pos = 29091869
    
    mock_session_class.return_value = mock_db_session
    mock_es_class.return_value = mock_es
    mock_db_session.query.return_value.yield_per.return_value = [variant]

    with patch("scripts.load_elasticsearch.INDEX_NAME", "test_index"):
        load_elasticsearch()

    actions = mock_bulk.call_args[0][1]
    assert len(actions) == 1
    assert actions[0]["_source"]["rules"] == [
        {"name": "PM2", "assessment": "MET"}
    ]
    assert len(actions[0]["_source"]["rules"]) == 1


@patch("scripts.load_elasticsearch._recreate_index")
@patch("scripts.load_elasticsearch.bulk")
@patch("scripts.load_elasticsearch.Elasticsearch")
@patch("scripts.load_elasticsearch.SessionLocal")
def test_load_es_batches_bulk_calls(
    mock_session_class, mock_es_class, mock_bulk, mock_recreate,
    mock_es, mock_db_session, tmp_path
):
    variants = []
    for i in range(1500):
        v = MagicMock()
        v.id = i
        v.rules = '[{"name": "PM2", "assessment": "MET"}]'
        v.classification = "Pathogenic"
        v.gene = "GENE"
        v.chr = "1"
        v.pos = 1000 + i
        variants.append(v)
    
    mock_session_class.return_value = mock_db_session
    mock_es_class.return_value = mock_es
    mock_db_session.query.return_value.yield_per.return_value = variants

    with patch("scripts.load_elasticsearch.INDEX_NAME", "test_index"):
        load_elasticsearch()

    assert mock_bulk.call_count == 2
    first_call_args = mock_bulk.call_args_list[0][0][1]
    second_call_args = mock_bulk.call_args_list[1][0][1]
    assert len(first_call_args) == 1000
    assert len(second_call_args) == 500