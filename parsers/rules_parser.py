import json
from typing import Dict
from typing import List


def parse_rules(rules_raw: str) -> List[Dict]:
    if not rules_raw:
        return []

    try:
        rules_data = json.loads(rules_raw)
    except json.JSONDecodeError:
        return []

    parsed_rules = []

    for rule in rules_data:
        rule_name = rule.get("name")
        assessment = rule.get("assessment")

        if not rule_name:
            continue

        parsed_rules.append(
            {
                "rule": rule_name,
                "assessment": assessment,
            }
        )

    return parsed_rules


def extract_met_rules(rules_raw: str) -> List[str]:
    parsed_rules = parse_rules(rules_raw)
    met_rules = set()

    for rule in parsed_rules:
        if rule["assessment"] == "MET":
            met_rules.add(rule["rule"])

    return list(met_rules)