import pytest
from parsers.rules_parser import parse_rules, extract_met_rules


class TestParseRules:
    def test_none_input(self):
        assert parse_rules(None) == []

    def test_empty_string(self):
        assert parse_rules("") == []

    def test_invalid_json(self):
        assert parse_rules("{invalid}") == []

    def test_whitespace_only(self):
        assert parse_rules("   ") == []

    def test_empty_list(self):
        assert parse_rules("[]") == []

    def test_single_rule(self):
        input_str = '[{"name": "PM2", "assessment": "MET"}]'
        expected = [{"rule": "PM2", "assessment": "MET"}]
        assert parse_rules(input_str) == expected

    def test_multiple_rules(self):
        input_str = '[{"name": "PM2", "assessment": "MET"}, {"name": "PVS1", "assessment": "STRONG"}]'
        expected = [
            {"rule": "PM2", "assessment": "MET"},
            {"rule": "PVS1", "assessment": "STRONG"}
        ]
        assert parse_rules(input_str) == expected

    def test_missing_name_skipped(self):
        input_str = '[{"name": "PM2", "assessment": "MET"}, {"assessment": "BENIGN"}]'
        expected = [{"rule": "PM2", "assessment": "MET"}]
        assert parse_rules(input_str) == expected

    def test_missing_assessment(self):
        input_str = '[{"name": "PP3"}]'
        expected = [{"rule": "PP3", "assessment": None}]
        assert parse_rules(input_str) == expected

    def test_extra_fields_ignored(self):
        input_str = '[{"name": "BS1", "assessment": "SUPPORTING", "evidence": "data"}]'
        expected = [{"rule": "BS1", "assessment": "SUPPORTING"}]
        assert parse_rules(input_str) == expected


class TestExtractMetRules:
    def test_no_met_rules(self):
        input_str = '[{"name": "PM2", "assessment": "STRONG"}]'
        assert extract_met_rules(input_str) == []

    def test_single_met_rule(self):
        input_str = '[{"name": "PVS1", "assessment": "MET"}]'
        result = extract_met_rules(input_str)
        assert set(result) == {"PVS1"}
        assert len(result) == 1

    def test_multiple_unique_met_rules(self):
        input_str = '[{"name": "PM2", "assessment": "MET"}, {"name": "PVS1", "assessment": "MET"}]'
        result = extract_met_rules(input_str)
        assert set(result) == {"PM2", "PVS1"}
        assert len(result) == 2

    def test_duplicate_met_rules(self):
        input_str = '[{"name": "PM2", "assessment": "MET"}, {"name": "PM2", "assessment": "MET"}]'
        result = extract_met_rules(input_str)
        assert set(result) == {"PM2"}
        assert len(result) == 1

    def test_mixed_assessments(self):
        input_str = '[{"name": "PM2", "assessment": "MET"}, {"name": "PP3", "assessment": "BENIGN"}]'
        result = extract_met_rules(input_str)
        assert result == ["PM2"]

    def test_invalid_input_returns_empty(self):
        assert extract_met_rules("") == []
        assert extract_met_rules("not json") == []

    def test_empty_list(self):
        assert extract_met_rules("[]") == []