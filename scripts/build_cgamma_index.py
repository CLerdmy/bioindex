import pickle
from pathlib import Path

from cgamma_src import cgamma
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

# Structure:
# [4 bytes]  magic "GAMM"
# [4 bytes]  num_rules
# for every rule:
#   [2 bytes]  rule_name_len
#   [N bytes]  rule_name (UTF-8)
#   [1 byte]   num_classifications
#   for every cls:
#     [1 byte]   class_name_len
#     [N bytes]  class_name (UTF-8)
#     [4 bytes]  encoded_bytes_len
#     [N bytes]  gamma compressed posting IDs (count + bytes)

def build_gamma_compressed_index_c(index_path=INDEX_PATH, output_path=CGAMMA_INDEX_PATH) -> None:
    """
    Build gamma-compressed index using C extension.
    
    Reads inverted index and encodes posting lists via cgamma C module.
    Stores in binary .cgamma format with magic header.
    
    Input: inverted_index.pkl
    Output: cgamma_index.cgamma
        Binary format: magic "GAMM" + {rule_name: {classification: bytes}}
    """

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