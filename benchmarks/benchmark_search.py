import json
import pickle
import time
from pathlib import Path

from elasticsearch import Elasticsearch
from sqlalchemy import text

from scripts.build_compressed_index_acmg import delta_decode

from db.session import engine


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


TEST_RULE = "PM2"


def benchmark_sql():
    query = text("""
        SELECT id, rules, classification
        FROM variants
    """)

    start = time.perf_counter()

    matched = set()

    allowed = {
        "Pathogenic",
        "LikelyPathogenic",
        "Benign",
        "LikelyBenign",
    }

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

        for variant_id, rules_raw, classification in rows:
            if classification not in allowed:
                continue

            if not rules_raw:
                continue

            try:
                rules = json.loads(rules_raw)
            except json.JSONDecodeError:
                continue

            for rule in rules:
                if (rule.get("name") == TEST_RULE and rule.get("assessment") == "MET"):
                    matched.add(variant_id)
                    break

    elapsed = time.perf_counter() - start

    print(
        f"SQL + JSON parsing: "
        f"{len(matched)} results | "
        f"{elapsed:.6f} sec"
    )


def benchmark_sql_like():
    query = text("""
        SELECT id, rules, classification
        FROM variants
        WHERE rules LIKE :pattern
    """)

    start = time.perf_counter()

    matched = set()

    allowed = {
        "Pathogenic",
        "LikelyPathogenic",
        "Benign",
        "LikelyBenign",
    }

    with engine.connect() as conn:

        rows = conn.execute(query, {"pattern": f'%"{TEST_RULE}"%'}).fetchall()

        for variant_id, rules_raw, classification in rows:
            if classification not in allowed:
                continue

            if not rules_raw:
                continue

            try:
                rules = json.loads(rules_raw)
            except json.JSONDecodeError:
                continue

            for rule in rules:
                if (rule.get("name") == TEST_RULE and rule.get("assessment") == "MET"):
                    matched.add(variant_id)
                    break

    elapsed = time.perf_counter() - start

    print(
        f"SQL LIKE + JSON parsing: "
        f"{len(matched)} results | "
        f"{elapsed:.6f} sec"
    )


def benchmark_inverted_index():
    with open(INDEX_PATH, "rb") as file:
        index = pickle.load(file)

    start = time.perf_counter()

    result = index.get(TEST_RULE, {})

    total = sum(
        len(v)
        for v in result.values()
    )

    elapsed = time.perf_counter() - start

    print(
        f"Inverted index: "
        f"{total} results | "
        f"{elapsed:.6f} sec"
    )


def benchmark_compressed_index():
    with open(COMPRESSED_INDEX_PATH, "rb") as file:
        compressed = pickle.load(file)

    start = time.perf_counter()

    result = compressed.get(TEST_RULE, {})

    decoded_total = 0

    for postings in result.values():
        decoded = delta_decode(postings)

        decoded_total += len(decoded)

    elapsed = time.perf_counter() - start

    print(
        f"Compressed index: "
        f"{decoded_total} results | "
        f"{elapsed:.6f} sec"
    )


def benchmark_elasticsearch():
    es = Elasticsearch("http://elasticsearch:9200")

    query = {
        "query": {
            "nested": {
                "path": "rules",
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"rules.name": TEST_RULE}},
                            {"term": {"rules.assessment": "MET"}}
                        ]
                    }
                }
            }
        }
    }

    start = time.perf_counter()

    response = es.search(
        index="variants",
        query=query["query"],
        track_total_hits=True
    )

    total = response["hits"]["total"]["value"]

    elapsed = time.perf_counter() - start

    print(
        f"Elasticsearch: "
        f"{total} results | "
        f"{elapsed:.6f} sec"
    )


if __name__ == "__main__":

    print(f"\nBenchmark for rule: {TEST_RULE}\n")

    benchmark_sql()

    benchmark_sql_like()

    benchmark_inverted_index()

    benchmark_compressed_index()

    benchmark_elasticsearch()