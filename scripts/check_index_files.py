import pickle
from pathlib import Path

from scripts.build_compressed_index_acmg import gamma_decode_postings


BASE_DIR = Path(__file__).resolve().parent.parent

INDEXES_DIR = (
    BASE_DIR
    / "data"
    / "indexes"
)

INVERTED_INDEX_PATH = (
    INDEXES_DIR
    / "inverted_index.pkl"
)

DELTA_INDEX_PATH = (
    INDEXES_DIR
    / "delta_compressed_index.pkl"
)

GAMMA_INDEX_PATH = (
    INDEXES_DIR
    / "gamma_compressed_index.pkl"
)


def get_file_size(path: Path) -> float:
    return path.stat().st_size / 1024


def load_pickle(path: Path):
    with open(path, "rb") as file:
        return pickle.load(file)


def count_total_postings(index: dict) -> int:
    total = 0

    for rule_data in index.values():
        for postings in rule_data.values():
            if isinstance(postings, bytes):
                decoded = gamma_decode_postings(postings)
                total += len(decoded)
            else:
                total += len(postings)

    return total


def count_rules(index: dict) -> int:
    return len(index)


def count_classifications(index: dict) -> int:
    classes = set()

    for rule_data in index.values():
        for cls in rule_data.keys():
            classes.add(cls)

    return len(classes)


def print_index_info(name: str, path: Path):
    print(f"\n=== {name} ===")

    if not path.exists():
        print("File not found")
        return

    size_kb = get_file_size(path)
    index = load_pickle(path)
    total_rules = count_rules(index)
    total_postings = count_total_postings(index)
    total_classes = count_classifications(index)

    print(f"Size: {size_kb:.2f} KB")
    print(f"Rules: {total_rules}")
    print(f"Classification groups: {total_classes}")
    print(f"Total postings: {total_postings}")


def print_compression_stats():
    original_size = get_file_size(INVERTED_INDEX_PATH)
    delta_size = get_file_size(DELTA_INDEX_PATH)
    gamma_size = get_file_size(GAMMA_INDEX_PATH)
    delta_ratio = ((1 - delta_size / original_size) * 100)
    gamma_ratio = ((1 - gamma_size / original_size) * 100)

    print("\n=== COMPRESSION STATS ===")
    print(f"Delta compression reduction: "f"{delta_ratio:.2f}%")
    print(f"Gamma compression reduction: "f"{gamma_ratio:.2f}%")


if __name__ == "__main__":
    print_index_info(
        "INVERTED INDEX",
        INVERTED_INDEX_PATH
    )

    print_index_info(
        "DELTA COMPRESSED INDEX",
        DELTA_INDEX_PATH
    )

    print_index_info(
        "GAMMA COMPRESSED INDEX",
        GAMMA_INDEX_PATH
    )

    print_compression_stats()