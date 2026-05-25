import pickle
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

_mock_cgamma = MagicMock()
_mock_cgamma_src = MagicMock()
sys.modules['cgamma'] = _mock_cgamma
sys.modules['cgamma_src'] = _mock_cgamma_src
sys.modules['cgamma_src.gamma_c'] = _mock_cgamma_src.gamma_c

from scripts.check_index_files import (
    get_file_size,
    load_pickle,
    count_total_postings,
    count_rules,
    count_classifications,
    print_index_info,
    print_compression_stats,
)
import scripts.check_index_files as cif


@pytest.fixture
def mock_path():
    return MagicMock(spec=Path)

def test_get_file_size(mock_path):
    mock_path.stat.return_value.st_size = 4096
    assert get_file_size(mock_path) == 4.0

def test_get_file_size_zero(mock_path):
    mock_path.stat.return_value.st_size = 0
    assert get_file_size(mock_path) == 0.0

def test_load_pickle(tmp_path):
    file = tmp_path / "test.pkl"
    data = {"rule": [1, 2, 3]}
    file.write_bytes(pickle.dumps(data))
    assert load_pickle(file) == data

def test_load_pickle_invalid_file(tmp_path):
    file = tmp_path / "empty.pkl"
    file.write_bytes(b"")
    with pytest.raises(Exception):
        load_pickle(file)

def test_count_rules():
    assert count_rules({"R1": {}, "R2": {}}) == 2

def test_count_classifications():
    index = {"R1": {"pathogenic": [1], "benign": [2]}, "R2": {"pathogenic": [3]}}
    assert count_classifications(index) == 2

def test_count_total_postings_standard():
    index = {"R1": {"pathogenic": [1, 2], "benign": [3]}}
    assert count_total_postings(index, is_cgamma=False) == 3

def test_count_total_postings_with_bytes():
    fake_decoded = [10, 20, 30]
    index = {"R1": {"pathogenic": b"compressed_data"}}
    with patch("scripts.check_index_files.gamma_decode_postings", return_value=fake_decoded):
        assert count_total_postings(index, is_cgamma=False) == 3

def test_print_index_info_file_not_found(capsys, tmp_path):
    print_index_info("Test Index", tmp_path / "missing.pkl")
    captured = capsys.readouterr()
    assert "File not found" in captured.out

def test_print_index_info_standard(capsys, tmp_path):
    file = tmp_path / "test.pkl"
    index = {"R1": {"pathogenic": [1, 2], "benign": [3]}}
    file.write_bytes(pickle.dumps(index))

    print_index_info("My Index", file, is_cgamma=False)
    captured = capsys.readouterr()
    assert "=== My Index ===" in captured.out
    assert "Rules: 1" in captured.out
    assert "Total postings: 3" in captured.out


@patch.object(cif, "cgamma")
def test_count_total_postings_cgamma(mock_cgamma):
    mock_cgamma.decode_postings.return_value = [1, 2, 3, 4] 
    index = {"R1": {"pathogenic": b"cgamma_payload"}}
    
    result = count_total_postings(index, is_cgamma=True)
    assert result == 4
    mock_cgamma.decode_postings.assert_called_once_with(b"cgamma_payload")


@patch.object(cif, "cgamma")
@patch.object(cif, "read_cgamma_file")
def test_print_index_info_cgamma(mock_read_cgamma, mock_cgamma, tmp_path, capsys):
    file = tmp_path / "test.cgamma"
    file.touch() 
    
    mock_read_cgamma.return_value = {
        "PM2": {"pathogenic": b"cgamma_data1", "benign": b"cgamma_data2"}
    }
    mock_cgamma.decode_postings.side_effect = [[10, 20], [30]]

    print_index_info("CGAMMA Test", file, is_cgamma=True)
    captured = capsys.readouterr()

    assert "=== CGAMMA Test ===" in captured.out
    assert "Size: 0.00 KB" in captured.out
    assert "Rules: 1" in captured.out
    assert "Classification groups: 2" in captured.out
    assert "Total postings: 3" in captured.out  
    
    mock_read_cgamma.assert_called_once_with(file)
    assert mock_cgamma.decode_postings.call_count == 2


@patch.object(cif, "get_file_size")
def test_print_compression_stats_with_cgamma(mock_get_size, capsys):
    mock_get_size.side_effect = [1000, 500, 250, 125]

    print_compression_stats()
    captured = capsys.readouterr()

    assert "Delta compression reduction: 50.00%" in captured.out
    assert "Gamma compression reduction: 75.00%" in captured.out
    assert "CGAMMA compression reduction: 87.50%" in captured.out
    
    assert mock_get_size.call_count == 4


@patch.object(cif, "get_file_size")
def test_print_compression_stats_zero_original(mock_get_size, capsys):
    mock_get_size.side_effect = [0, 0, 0, 0]
    
    with pytest.raises(ZeroDivisionError):
        print_compression_stats()