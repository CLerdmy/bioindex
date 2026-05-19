import pickle
from pathlib import Path

from db.models import VariantDB
from db.session import SessionLocal


BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = (
    BASE_DIR
    / "data"
    / "indexes"
    / "inverted_index.pkl"
)


def load_index():
    with open(INDEX_PATH, "rb") as file:
        return pickle.load(file)

def test_specific_rule(rule_name: str):
    index = load_index()

    if rule_name not in index:
        print(f"Rule {rule_name} not found in index")
        return

    print(f"\nRule: {rule_name}")
    for cls, variants in index[rule_name].items():
        print(f"{cls}: {variants[:10]}")

    print_variants_details(index["PM2"]["pathogenic"][:5])

def print_variants_details(ids: list[int]):
    db = SessionLocal()

    variants = (db.query(VariantDB).filter(VariantDB.id.in_(ids)).all())

    for variant in variants:
        print(
            f"ID={variant.id} | "
            f"{variant.chr}:{variant.pos} "
            f"{variant.ref}>{variant.alt} | "
            f"{variant.gene} | "
            f"{variant.classification}"
        )

    db.close()

if __name__ == "__main__":

    test_specific_rule("PM2")