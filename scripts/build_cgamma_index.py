import pickle
from pathlib import Path

import cgamma
from cgamma_src.gamma_c import write_cgamma_file


BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = (
    BASE_DIR 
    / "data" 
    / "indexes" 
    / "inverted_index.pkl"
)

CGAMMA_INDEX_PATH = (
    BASE_DIR 
    / "data" 
    / "indexes" 
    / "cgamma_index.cgamma"
)


def build_gamma_compressed_index_c(index_path=INDEX_PATH, output_path=CGAMMA_INDEX_PATH) -> None:
    with open(index_path, "rb") as file:
        inverted_index: dict = pickle.load(file)

    encoded_index = {}
    total_ids = 0

    for rule_name, classifications in inverted_index.items():
        encoded_index[rule_name] = {}
        for cls_name, ids in classifications.items():
            encoded_index[rule_name][cls_name] = cgamma.encode_postings(ids)
            total_ids += len(ids)

    write_cgamma_file(encoded_index, output_path)


if __name__ == "__main__":
    build_gamma_compressed_index_c()