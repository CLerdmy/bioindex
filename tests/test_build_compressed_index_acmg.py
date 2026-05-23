import pickle
import pytest
from unittest.mock import patch, MagicMock
from scripts.build_compressed_index_acmg import (
    _delta_encode,
    delta_decode,
    gamma_encode_number,
    gamma_decode_stream,
    bits_to_bytes,
    bytes_to_bits,
    gamma_decode_postings,
    build_delta_compressed_index,
    build_gamma_compressed_index,
)

def test_delta_encode_normal():
    assert _delta_encode([10, 12, 15, 20]) == [10, 2, 3, 5]

def test_delta_encode_single():
    assert _delta_encode([42]) == [42]

def test_delta_encode_empty():
    assert _delta_encode([]) == []

def test_delta_encode_already_sequential():
    assert _delta_encode([1, 2, 3, 4]) == [1, 1, 1, 1]


def test_delta_decode_normal():
    assert delta_decode([10, 2, 3, 5]) == [10, 12, 15, 20]

def test_delta_decode_single():
    assert delta_decode([42]) == [42]

def test_delta_decode_empty():
    assert delta_decode([]) == []

def test_delta_roundtrip():
    original = [5, 10, 15, 20, 25]
    encoded = _delta_encode(original)
    assert delta_decode(encoded) == original


def test_gamma_encode_number():
    assert gamma_encode_number(1) == "1"
    assert gamma_encode_number(2) == "010"
    assert gamma_encode_number(4) == "00100"
    assert gamma_encode_number(10) == "0001010"

def test_gamma_encode_invalid():
    with pytest.raises(ValueError, match="Supports only positive integers"):
        gamma_encode_number(0)
    with pytest.raises(ValueError, match="Supports only positive integers"):
        gamma_encode_number(-5)


def test_gamma_decode_stream():
    assert gamma_decode_stream("1") == [1]
    assert gamma_decode_stream("010") == [2]
    assert gamma_decode_stream("001000001010") == [4, 10]

def test_gamma_decode_stream_empty():
    assert gamma_decode_stream("") == []

def test_gamma_stream_roundtrip():
    numbers = [1, 3, 7, 15]
    bitstream = "".join(gamma_encode_number(n) for n in numbers)
    assert gamma_decode_stream(bitstream) == numbers


def test_bits_to_bytes_no_padding():
    assert bits_to_bytes("11110000") == b"\x00\xf0"

def test_bits_to_bytes_with_padding():
    assert bits_to_bytes("11010") == b"\x03\xd0"  

def test_bits_to_bytes_empty():
    assert bits_to_bytes("") == b"\x00"

def test_bytes_to_bits_roundtrip():
    original = "1101000011110000"
    packed = bits_to_bytes(original)
    assert bytes_to_bits(packed) == original

def test_bytes_to_bits_empty():
    assert bytes_to_bits(b"\x00") == ""


def test_gamma_decode_postings():
    original = [10, 12, 15, 20]
    delta_enc = _delta_encode(original)
    bitstream = "".join(gamma_encode_number(n) for n in delta_enc)
    packed = bits_to_bytes(bitstream)
    
    assert gamma_decode_postings(packed) == original

def test_gamma_decode_postings_single():
    original = [100]
    delta_enc = _delta_encode(original)
    bitstream = "".join(gamma_encode_number(n) for n in delta_enc)
    packed = bits_to_bytes(bitstream)
    assert gamma_decode_postings(packed) == original

def test_gamma_decode_postings_empty():
    assert gamma_decode_postings(b"\x00") == []


@pytest.fixture
def mock_inverted_index():
    return {
        "PM2": {"pathogenic": [10, 20, 30], "benign": [5]},
        "PVS1": {"pathogenic": [100, 105]},
    }

@patch("scripts.build_compressed_index_acmg.pickle")
@patch("scripts.build_compressed_index_acmg.open", new_callable=MagicMock)
def test_build_delta_compressed_index(mock_open, mock_pickle, mock_inverted_index, tmp_path):
    mock_pickle.load.return_value = mock_inverted_index
    
    with patch("scripts.build_compressed_index_acmg.COMPRESSED_INDEX_PATH", tmp_path / "delta.pkl"):
        build_delta_compressed_index()

    call_args = mock_pickle.dump.call_args[0]
    dumped_index = call_args[0]
    
    assert dumped_index["PM2"]["pathogenic"] == [10, 10, 10]  
    assert dumped_index["PM2"]["benign"] == [5]
    assert dumped_index["PVS1"]["pathogenic"] == [100, 5]
    assert mock_pickle.dump.call_count == 1


@patch("scripts.build_compressed_index_acmg.pickle")
@patch("scripts.build_compressed_index_acmg.open", new_callable=MagicMock)
def test_build_gamma_compressed_index(mock_open, mock_pickle, mock_inverted_index, tmp_path):
    mock_pickle.load.return_value = mock_inverted_index
    
    with patch("scripts.build_compressed_index_acmg.COMPRESSED_INDEX_PATH", tmp_path / "gamma.pkl"):
        build_gamma_compressed_index()

    call_args = mock_pickle.dump.call_args[0]
    dumped_index = call_args[0]
    
    assert isinstance(dumped_index["PM2"]["pathogenic"], bytes)
    assert isinstance(dumped_index["PM2"]["benign"], bytes)
    assert isinstance(dumped_index["PVS1"]["pathogenic"], bytes)
    
    decoded = gamma_decode_postings(dumped_index["PM2"]["pathogenic"])
    assert decoded == [10, 20, 30]
    assert mock_pickle.dump.call_count == 1