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

RUNS = 5

ALLOWED_CLASSIFICATIONS = {
    "Pathogenic",
    "LikelyPathogenic",
    "Benign",
    "LikelyBenign",
}

AND_QUERIES = [
    ("PM2", "PVS1"),
    ("PM2", "PP3"),
    ("BS1", "PP3"),
]


def build_ground_truth():
    query = text("""
        SELECT id, rules, classification
        FROM variants
    """)

    truth = {}

    with engine.connect() as conn:

        rows = conn.execute(query).fetchall()

        for rule_a, rule_b in AND_QUERIES:

            matched = set()

            for variant_id, rules_raw, classification in rows:

                if classification not in ALLOWED_CLASSIFICATIONS:
                    continue

                if not rules_raw:
                    continue

                try:
                    rules = json.loads(rules_raw)
                except json.JSONDecodeError:
                    continue

                met_rules = set()

                for rule in rules:

                    if rule.get("assessment") == "MET":
                        met_rules.add(rule.get("name"))

                if (
                    rule_a in met_rules
                    and rule_b in met_rules
                ):
                    matched.add(variant_id)

            truth[(rule_a, rule_b)] = matched

    return truth


def search_sql_full(rule_a, rule_b):
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

            met_rules = set()

            for rule in rules:

                if rule.get("assessment") == "MET":
                    met_rules.add(rule.get("name"))

            if (
                rule_a in met_rules
                and rule_b in met_rules
            ):
                matched.add(variant_id)

    return matched


def search_sql_like(rule_a, rule_b):
    query = text("""
        SELECT id, rules, classification
        FROM variants
        WHERE rules LIKE :pattern_a
        AND rules LIKE :pattern_b
    """)

    matched = set()

    with engine.connect() as conn:

        rows = conn.execute(
            query,
            {
                "pattern_a": f'%"name": "{rule_a}"%',
                "pattern_b": f'%"name": "{rule_b}"%',
            }
        ).fetchall()

        for variant_id, rules_raw, classification in rows:

            if classification not in ALLOWED_CLASSIFICATIONS:
                continue

            if not rules_raw:
                continue

            try:
                rules = json.loads(rules_raw)
            except json.JSONDecodeError:
                continue

            met_rules = set()

            for rule in rules:

                if rule.get("assessment") == "MET":
                    met_rules.add(rule.get("name"))

            if (
                rule_a in met_rules
                and rule_b in met_rules
            ):
                matched.add(variant_id)

    return matched


with open(INDEX_PATH, "rb") as file:
    INVERTED_INDEX = pickle.load(file)


def search_inverted(rule_a, rule_b):
    set_a = set()
    set_b = set()

    for postings in INVERTED_INDEX.get(rule_a, {}).values():
        set_a.update(postings)

    for postings in INVERTED_INDEX.get(rule_b, {}).values():
        set_b.update(postings)

    return set_a & set_b


with open(COMPRESSED_INDEX_PATH, "rb") as file:
    COMPRESSED_INDEX = pickle.load(file)


def search_compressed(rule_a, rule_b):
    set_a = set()
    set_b = set()

    for postings in COMPRESSED_INDEX.get(rule_a, {}).values():
        set_a.update(gamma_decode_postings(postings))

    for postings in COMPRESSED_INDEX.get(rule_b, {}).values():
        set_b.update(gamma_decode_postings(postings))

    return set_a & set_b


import cgamma
from cgamma_src.gamma_c import read_cgamma_file

CGAMMA_INDEX = read_cgamma_file(CGAMMA_INDEX_PATH)

def search_cgamma(rule_a, rule_b):
    set_a = set()
    set_b = set()

    for encoded in CGAMMA_INDEX.get(rule_a, {}).values():
        set_a.update(cgamma.decode_postings(encoded))

    for encoded in CGAMMA_INDEX.get(rule_b, {}).values():
        set_b.update(cgamma.decode_postings(encoded))

    return set_a & set_b


ES = Elasticsearch("http://elasticsearch:9200")


def search_elasticsearch(rule_a, rule_b):
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "nested": {
                            "path": "rules",
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "term": {
                                                "rules.name": rule_a
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
                    },
                    {
                        "nested": {
                            "path": "rules",
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "term": {
                                                "rules.name": rule_b
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
                ]
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


def benchmark_method(name, search_func, ground_truth):
    print(f"\n=== {name} ===\n")

    all_times = []

    for rule_a, rule_b in AND_QUERIES:
        expected = ground_truth[(rule_a, rule_b)]

        timings = []

        actual = None

        for _ in range(RUNS):
            start = time.perf_counter()

            actual = search_func(rule_a, rule_b)

            elapsed = time.perf_counter() - start

            timings.append(elapsed)

        validate(
            f"{name} :: {rule_a} AND {rule_b}",
            expected,
            actual
        )

        avg_time = statistics.mean(timings)

        all_times.extend(timings)

        print(
            f"{rule_a} AND {rule_b:<6} | "
            f"results={len(actual):<6} | "
            f"avg={avg_time:.6f} sec"
        )

    total_avg = statistics.mean(all_times)

    print(f"\nTOTAL AVG: {total_avg:.6f} sec")


if __name__ == "__main__":
    ground_truth = build_ground_truth()

    # benchmark_method(
    #     "SQL FULL SCAN",
    #     search_sql_full,
    #     ground_truth
    # )

    # benchmark_method(
    #     "SQL LIKE",
    #     search_sql_like,
    #     ground_truth
    # )

    # benchmark_method(
    #     "INVERTED INDEX",
    #     search_inverted,
    #     ground_truth
    # )

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