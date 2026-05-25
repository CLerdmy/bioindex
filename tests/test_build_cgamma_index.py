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

from scripts.build_cgamma_index import build_gamma_compressed_index_c
import scripts.build_cgamma_index as bci


@patch.object(bci, "write_cgamma_file")
@patch.object(bci, "cgamma")
@patch("builtins.open")
def test_build_index_empty(mock_open, mock_cgamma, mock_write, tmp_path):
    """Пустой индекс → записывается пустой cgamma-файл"""
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    with patch("pickle.load", return_value={}):
        output = tmp_path / "empty.cgamma"
        build_gamma_compressed_index_c(output_path=output)

    mock_cgamma.encode_postings.assert_not_called()
    mock_write.assert_called_once()
    call_args = mock_write.call_args
    assert call_args[0][0] == {}  
    assert call_args[0][1] == output


@patch.object(bci, "write_cgamma_file")
@patch.object(bci, "cgamma")
@patch("builtins.open")
def test_build_index_single_rule(mock_open, mock_cgamma, mock_write, tmp_path):
    """Один правило с одной классификацией"""
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    mock_index = {"PM2": {"pathogenic": [1, 2, 3]}}
    mock_cgamma.encode_postings.return_value = b"encoded_pm2_pathogenic"
    
    with patch("pickle.load", return_value=mock_index):
        output = tmp_path / "single.cgamma"
        build_gamma_compressed_index_c(output_path=output)

    mock_cgamma.encode_postings.assert_called_once_with([1, 2, 3])
    
    mock_write.assert_called_once()
    encoded_index = mock_write.call_args[0][0]
    assert encoded_index == {"PM2": {"pathogenic": b"encoded_pm2_pathogenic"}}
    assert mock_write.call_args[0][1] == output


@patch.object(bci, "write_cgamma_file")
@patch.object(bci, "cgamma")
@patch("builtins.open")
def test_build_index_multiple_rules(mock_open, mock_cgamma, mock_write, tmp_path):
    """Несколько правил с несколькими классификациями"""
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    mock_index = {
        "PM2": {"pathogenic": [1, 2], "benign": [3, 4]},
        "PVS1": {"pathogenic": [5, 6, 7]},
    }
    mock_cgamma.encode_postings.side_effect = [
        b"enc_pm2_path", b"enc_pm2_ben", b"enc_pvs1_path"
    ]
    
    with patch("pickle.load", return_value=mock_index):
        output = tmp_path / "multi.cgamma"
        build_gamma_compressed_index_c(output_path=output)

    assert mock_cgamma.encode_postings.call_count == 3
    
    calls = mock_cgamma.encode_postings.call_args_list
    assert calls[0][0][0] == [1, 2]  
    assert calls[1][0][0] == [3, 4]   
    assert calls[2][0][0] == [5, 6, 7]  
    
    encoded_index = mock_write.call_args[0][0]
    assert encoded_index["PM2"]["pathogenic"] == b"enc_pm2_path"
    assert encoded_index["PM2"]["benign"] == b"enc_pm2_ben"
    assert encoded_index["PVS1"]["pathogenic"] == b"enc_pvs1_path"


@patch.object(bci, "write_cgamma_file")
@patch.object(bci, "cgamma")
@patch("builtins.open")
def test_build_index_with_empty_postings(mock_open, mock_cgamma, mock_write, tmp_path):
    """Правило с пустым списком ID"""
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    mock_index = {"PM2": {"pathogenic": []}}
    mock_cgamma.encode_postings.return_value = b"empty_encoded"
    
    with patch("pickle.load", return_value=mock_index):
        output = tmp_path / "empty_postings.cgamma"
        build_gamma_compressed_index_c(output_path=output)

    mock_cgamma.encode_postings.assert_called_once_with([])
    
    encoded_index = mock_write.call_args[0][0]
    assert encoded_index["PM2"]["pathogenic"] == b"empty_encoded"


@patch.object(bci, "write_cgamma_file")
@patch.object(bci, "cgamma")
@patch("builtins.open")
def test_build_index_custom_paths(mock_open, mock_cgamma, mock_write, tmp_path):
    """Проверяем, что функция работает с кастомными путями, а не только с дефолтными"""
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    mock_index = {"BS1": {"benign": [100, 200]}}
    mock_cgamma.encode_postings.return_value = b"bs1_ben_encoded"
    
    custom_input = tmp_path / "custom_in.pkl"
    custom_output = tmp_path / "custom_out.cgamma"
    
    with patch("pickle.load", return_value=mock_index):
        build_gamma_compressed_index_c(
            index_path=custom_input,
            output_path=custom_output
        )

    mock_open.assert_called_once_with(custom_input, "rb")
    assert mock_write.call_args[0][1] == custom_output