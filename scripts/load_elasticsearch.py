import json

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from db.models import VariantDB
from db.session import SessionLocal


INDEX_NAME = "variants"

ALLOWED_CLASSIFICATIONS = {
    "Pathogenic": "pathogenic",
    "LikelyPathogenic": "pathogenic",
    "Benign": "benign",
    "LikelyBenign": "likely_benign",
}

def load_elasticsearch():
    es = Elasticsearch("http://elasticsearch:9200")

    _recreate_index(es)

    db = SessionLocal()

    variants = db.query(VariantDB).yield_per(1000)

    actions = []

    for variant in variants:
        normalized_classification = ALLOWED_CLASSIFICATIONS.get(variant.classification)

        if normalized_classification is None:
            continue

        rules_raw = variant.rules or "[]"

        try:
            rules_data = json.loads(rules_raw)
        except json.JSONDecodeError:
            rules_data = []

        filtered_rules = []
        seen_rules = set()

        for rule in rules_data:
            name = rule.get("name")
            assessment = rule.get("assessment")

            if not name:
                continue

            if assessment == "MET":

                if name in seen_rules:
                    continue

                seen_rules.add(name)

                filtered_rules.append({
                    "name": name,
                    "assessment": "MET"
                })

        doc = {
            "_index": INDEX_NAME,
            "_id": variant.id,
            "_source": {
                "variant_id": variant.id,
                "classification": normalized_classification,
                "gene": variant.gene,
                "chr": variant.chr,
                "pos": variant.pos,
                "rules": filtered_rules
            },
        }

        actions.append(doc)

        if len(actions) >= 1000:
            bulk(es, actions)
            actions = []

    if actions:
        bulk(es, actions)

    db.close()


def _recreate_index(es):

    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)

    mappings = {
        "mappings": {
            "properties": {
                "variant_id": {"type": "integer"},
                "classification": {"type": "keyword"},
                "gene": {"type": "keyword"},
                "chr": {"type": "keyword"},
                "pos": {"type": "integer"},
                "rules": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "keyword"},
                        "assessment": {"type": "keyword"}
                    }
                }
            }
        }
    }

    es.indices.create(index=INDEX_NAME, body=mappings)


if __name__ == "__main__":
    load_elasticsearch()