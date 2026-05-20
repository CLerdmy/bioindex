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


def build_compressed_index():
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


if __name__ == "__main__":

    build_compressed_index()