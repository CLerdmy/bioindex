import json
import pickle
from collections import defaultdict
from pathlib import Path

from db.models import VariantDB
from db.session import SessionLocal

from parsers.rules_parser import extract_met_rules


BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = (
    BASE_DIR
    / "data"
    / "indexes"
    / "inverted_index.pkl"
)

INDEX_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

# Structure:
# {
#   rule_name: str -> {
#     classification: str -> [variant_id: int, ...]  (sorted)
#   }
# }

def build_inverted_index_acmg() -> None:
    """
    Build inverted index from database.
    
    Reads all variants from DB, extracts MET rules, normalizes classifications,
    and stores index as pickle.
    
    Output: inverted_index.pkl
        {rule_name: {classification: [variant_id, ...]}}
    """

    db = SessionLocal()

    inverted_index = defaultdict(lambda: defaultdict(list))

    variants = db.query(VariantDB).yield_per(1000)

    for variant in variants:
        met_rules = extract_met_rules(variant.rules)
        classification = _normalize_classification(variant.classification)
        
        if classification is None:
            continue

        for rule_name in met_rules:
            inverted_index[rule_name][classification].append(variant.id)

    for rule_name in inverted_index:
        for classification in inverted_index[rule_name]:
            inverted_index[rule_name][classification].sort()

    with open(INDEX_PATH, "wb") as file:
        pickle.dump(dict(inverted_index), file,)

    _save_metadata(len(inverted_index))

    db.close()

def _normalize_classification(value: str) -> str | None:
    mapping = {
        "Pathogenic": "pathogenic",
        "LikelyPathogenic": "pathogenic",
        "Benign": "benign",
        "LikelyBenign": "likely_benign",
    }

    return mapping.get(value)

def _save_metadata(total_rules: int) -> None:
    METADATA_PATH = (
        BASE_DIR
        / "data"
        / "indexes"
        / "metadata.json"
    )

    metadata = {
        "index_type": "acmg_inverted_index",
        "total_rules": total_rules,
        "classification_groups": [
            "pathogenic",
            "benign",
            "likely_benign",
        ],
    }

    with open(METADATA_PATH, "w") as file:
        json.dump(metadata, file, indent=4)

if __name__ == "__main__":

    build_inverted_index_acmg()