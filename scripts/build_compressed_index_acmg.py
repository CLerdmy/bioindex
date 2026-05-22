import pickle
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = (
    BASE_DIR
    / "data"
    / "indexes"
    / "inverted_index.pkl"
)

COMPRESSED_INDEX_PATH = (
    BASE_DIR
    / "data"
    / "indexes"
    / "compressed_index.pkl"
)


def build_delta_compressed_index():
    with open(INDEX_PATH, "rb") as file:
        inverted_index = pickle.load(file)

    compressed_index = {}

    for rule_name in inverted_index:

        compressed_index[rule_name] = {}

        for classification in inverted_index[rule_name]:
            postings = inverted_index[rule_name][classification]

            compressed_postings = _delta_encode(postings)

            compressed_index[rule_name][classification] = compressed_postings

    with open(COMPRESSED_INDEX_PATH, "wb") as file:
        pickle.dump(compressed_index, file,)


def _delta_encode(postings: list[int]) -> list[int]:
    if not postings:
        return []

    encoded = [postings[0]]

    for i in range(1, len(postings)):
        delta = (postings[i] - postings[i - 1])
        encoded.append(delta)

    return encoded


def delta_decode(encoded_postings: list[int]) -> list[int]:
    if not encoded_postings:
        return []

    decoded = [encoded_postings[0]]

    for delta in encoded_postings[1:]:
        decoded.append(decoded[-1] + delta)

    return decoded


def build_gamma_compressed_index():
    with open(INDEX_PATH, "rb") as file:
        inverted_index = pickle.load(file)

    gamma_index = {}

    for rule_name in inverted_index:
        gamma_index[rule_name] = {}

        for classification in inverted_index[rule_name]:
            postings = inverted_index[rule_name][classification]

            delta_encoded = _delta_encode(postings)

            bitstream = ""

            for number in delta_encoded:
                bitstream += gamma_encode_number(number)

            packed_bytes = bits_to_bytes(bitstream)

            gamma_index[rule_name][classification] = packed_bytes

    with open(COMPRESSED_INDEX_PATH, "wb") as file:
        pickle.dump(gamma_index, file)


def gamma_encode_number(n: int) -> str:
    if n <= 0:
        raise ValueError("Supports only positive integers")

    binary = bin(n)[2:]
    offset = binary[1:]
    unary = ("0" * len(offset)) + "1"

    return unary + offset


def gamma_decode_stream(bitstream: str) -> list[int]:
    numbers = []
    i = 0
    while i < len(bitstream):
        zero_count = 0

        while i < len(bitstream) and bitstream[i] == "0":
            zero_count += 1
            i += 1

        if i >= len(bitstream):
            break

        i += 1

        offset = bitstream[i:i + zero_count]
        i += zero_count
        binary = "1" + offset
        numbers.append(int(binary, 2))

    return numbers


def bits_to_bytes(bitstring: str) -> bytes:
    padding = (8 - len(bitstring) % 8) % 8
    bitstring += "0" * padding
    result = bytearray()

    for i in range(0, len(bitstring), 8):
        byte = bitstring[i:i + 8]
        result.append(int(byte, 2))

    return bytes([padding]) + bytes(result)


def bytes_to_bits(data: bytes) -> str:
    padding = data[0]
    binary = ""

    for byte in data[1:]:
        binary += f"{byte:08b}"

    if padding:
        binary = binary[:-padding]

    return binary


def gamma_decode_postings(encoded_bytes: bytes) -> list[int]:

    bitstream = bytes_to_bits(encoded_bytes)

    delta_encoded = gamma_decode_stream(bitstream)

    return delta_decode(delta_encoded)


if __name__ == "__main__":

    build_gamma_compressed_index()