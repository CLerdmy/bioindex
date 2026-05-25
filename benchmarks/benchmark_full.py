import json
import pickle
import statistics
import time
from pathlib import Path

from elasticsearch import Elasticsearch
from sqlalchemy import text

from db.session import engine
from scripts.build_compressed_index_acmg import delta_decode, gamma_decode_postings


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

CGAMMA_INDEX_PATH = (
    BASE_DIR
    / "data"
    / "indexes"
    / "cgamma_index.cgamma"
)

RULES_TO_TEST = [
    "PM2",
    "PVS1",
    "PP3",
    "BS1",
    "PS1",
]

RUNS = 5

ALLOWED_CLASSIFICATIONS = {
    "Pathogenic",
    "LikelyPathogenic",
    "Benign",
    "LikelyBenign",
}

def build_ground_truth():
    query = text("""
        SELECT id, rules, classification
        FROM variants
    """)

    ground_truth = {
        rule: set()
        for rule in RULES_TO_TEST
    }

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

        for variant_id, rules_raw, classification in rows:
            if classification not in ALLOWED_CLASSIFICATIONS:
                continue

            if not rules_raw:
                continue

            try:
                rules = json.loads(rules_raw)
            except json.JSONDecodeError:
                continue

            for rule in rules:
                name = rule.get("name")
                assessment = rule.get("assessment")

                if (name in RULES_TO_TEST and assessment == "MET"):
                    ground_truth[name].add(variant_id)

    return ground_truth


def search_sql_full(rule_name):
    query = text("""
        SELECT id, rules, classification
        FROM variants
    """)

    matched = set()

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

        for variant_id, rules_raw, classification in rows:
            if classification not in ALLOWED_CLASSIFICATIONS:
                continue

            if not rules_raw:
                continue

            try:
                rules = json.loads(rules_raw)
            except json.JSONDecodeError:
                continue

            for rule in rules:
                if (rule.get("name") == rule_name and rule.get("assessment") == "MET"):
                    matched.add(variant_id)
                    break

    return matched


def search_sql_like(rule_name):
    query = text("""
        SELECT id, rules, classification
        FROM variants
        WHERE rules LIKE :pattern
    """)

    matched = set()

    with engine.connect() as conn:
        rows = conn.execute(query, {"pattern": f'%"name": "{rule_name}"%'}).fetchall()

        for variant_id, rules_raw, classification in rows:
            if classification not in ALLOWED_CLASSIFICATIONS:
                continue

            if not rules_raw:
                continue

            try:
                rules = json.loads(rules_raw)
            except json.JSONDecodeError:
                continue

            for rule in rules:
                if (rule.get("name") == rule_name and rule.get("assessment") == "MET"):
                    matched.add(variant_id)
                    break

    return matched


with open(INDEX_PATH, "rb") as file:
    INVERTED_INDEX = pickle.load(file)


def search_inverted(rule_name):
    result = INVERTED_INDEX.get(rule_name, {})

    matched = set()

    for postings in result.values():
        matched.update(postings)

    return matched


with open(COMPRESSED_INDEX_PATH, "rb") as file:
    COMPRESSED_INDEX = pickle.load(file)


def search_compressed(rule_name):
    result = COMPRESSED_INDEX.get(rule_name, {})

    matched = set()

    for postings in result.values():

        decoded = gamma_decode_postings(postings)

        matched.update(decoded)

    return matched


from cgamma_src import cgamma
from cgamma_src.gamma_c import read_cgamma_file


def search_cgamma(rule_name):
    index = read_cgamma_file(CGAMMA_INDEX_PATH)
    matched = set()
    for encoded in index.get(rule_name, {}).values():
        matched.update(cgamma.decode_postings(encoded))
    return matched


ES = Elasticsearch("http://elasticsearch:9200")


def search_elasticsearch(rule_name):
    query = {
        "query": {
            "nested": {
                "path": "rules",
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "rules.name": rule_name
                                }
                            },
                            {
                                "term": {
                                    "rules.assessment": "MET"
                                }
                            }
                        ]
                    }
                }
            }
        }
    }

    response = ES.search(
        index="variants",
        query=query["query"],
        size=10000
    )

    matched = set()

    for hit in response["hits"]["hits"]:
        matched.add(int(hit["_id"]))

    return matched


def validate(name, expected, actual):

    if expected == actual:
        print(f"VALIDATION [{name}] PASSED")
        return

    missing = len(expected - actual)
    extra = len(actual - expected)

    print(f"VALIDATION [{name}] FAILED")
    print(f"Missing: {missing}")
    print(f"Extra: {extra}")


def benchmark_method(method_name, search_func, ground_truth):

    print(f"\n=== {method_name} ===\n")

    all_times = []

    for rule_name in RULES_TO_TEST:

        expected = ground_truth[rule_name]

        timings = []

        actual = None

        for _ in range(RUNS):

            start = time.perf_counter()

            actual = search_func(rule_name)

            elapsed = time.perf_counter() - start

            timings.append(elapsed)

        validate(
            f"{method_name} :: {rule_name}",
            expected,
            actual
        )

        avg_time = statistics.mean(timings)

        all_times.extend(timings)

        print(
            f"{rule_name:<6} | "
            f"results={len(actual):<6} | "
            f"avg={avg_time:.6f} sec"
        )

    total_avg = statistics.mean(all_times)

    print(f"\nTOTAL AVG: {total_avg:.6f} sec")


if __name__ == "__main__":

    ground_truth = build_ground_truth()

    benchmark_method(
        "SQL FULL SCAN",
        search_sql_full,
        ground_truth
    )

    benchmark_method(
        "SQL LIKE",
        search_sql_like,
        ground_truth
    )

    benchmark_method(
        "INVERTED INDEX",
        search_inverted,
        ground_truth
    )

    benchmark_method(
        "COMPRESSED INDEX",
        search_compressed,
        ground_truth
    )

    benchmark_method(
        "CGAMMA INDEX",
        search_cgamma,
        ground_truth
    )

    benchmark_method(
        "ELASTICSEARCH",
        search_elasticsearch,
        ground_truth
    )