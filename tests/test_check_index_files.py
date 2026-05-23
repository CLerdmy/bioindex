import pickle
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.check_index_files import (
    get_file_size,
    load_pickle,
    count_total_postings,
    count_rules,
    count_classifications,
    print_index_info,
    print_compression_stats,
)


@pytest.fixture
def mock_path():
    """Фикстура для эмуляции pathlib.Path без реальных файлов."""
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
    index = {"R1": {}, "R2": {}, "R3": {}}
    assert count_rules(index) == 3


def test_count_rules_empty():
    assert count_rules({}) == 0


def test_count_classifications():
    index = {
        "R1": {"pathogenic": [1], "benign": [2]},
        "R2": {"pathogenic": [3], "likely_benign": [4]},
    }
    assert count_classifications(index) == 3


def test_count_classifications_duplicates():
    index = {
        "R1": {"pathogenic": [1]},
        "R2": {"pathogenic": [2]},
    }
    assert count_classifications(index) == 1


def test_count_total_postings():
    index = {
        "R1": {"pathogenic": [1, 2], "benign": [3]},
        "R2": {"pathogenic": [4, 5, 6]},
    }
    assert count_total_postings(index) == 6


def test_count_total_postings_with_bytes():
    fake_decoded = [10, 20, 30]
    index = {"R1": {"pathogenic": b"compressed_data"}}
    with patch("scripts.check_index_files.gamma_decode_postings", return_value=fake_decoded):
        assert count_total_postings(index) == 3


def test_count_total_postings_empty():
    assert count_total_postings({}) == 0


def test_print_index_info_file_not_found(capsys, tmp_path):
    non_existent = tmp_path / "missing.pkl"
    print_index_info("Test Index", non_existent)
    captured = capsys.readouterr()
    assert "File not found" in captured.out


def test_print_index_info_exists(capsys, tmp_path):
    file = tmp_path / "test.pkl"
    index = {"R1": {"pathogenic": [1, 2], "benign": [3]}}
    file.write_bytes(pickle.dumps(index))

    with patch("scripts.check_index_files.gamma_decode_postings", return_value=[1, 2]):
        print_index_info("My Index", file)

    captured = capsys.readouterr()
    assert "=== My Index ===" in captured.out
    assert "Rules: 1" in captured.out
    assert "Classification groups: 2" in captured.out
    assert "Total postings: 3" in captured.out
    assert "Size:" in captured.out

def test_print_compression_stats(capsys, tmp_path):
    orig = tmp_path / "orig.pkl"
    delta = tmp_path / "delta.pkl"
    gamma = tmp_path / "gamma.pkl"

    orig.write_bytes(b"a" * 1000)
    delta.write_bytes(b"a" * 500) 
    gamma.write_bytes(b"a" * 250) 

    with patch("scripts.check_index_files.INVERTED_INDEX_PATH", orig), \
         patch("scripts.check_index_files.DELTA_INDEX_PATH", delta), \
         patch("scripts.check_index_files.GAMMA_INDEX_PATH", gamma):
        print_compression_stats()

    captured = capsys.readouterr()
    assert "Delta compression reduction: 50.00%" in captured.out
    assert "Gamma compression reduction: 75.00%" in captured.out


def test_print_compression_stats_no_reduction(capsys, tmp_path):
    f = tmp_path / "same.pkl"
    f.write_bytes(b"x" * 100)

    with patch("scripts.check_index_files.INVERTED_INDEX_PATH", f), \
         patch("scripts.check_index_files.DELTA_INDEX_PATH", f), \
         patch("scripts.check_index_files.GAMMA_INDEX_PATH", f):
        print_compression_stats()

    captured = capsys.readouterr()
    assert "0.00%" in captured.out