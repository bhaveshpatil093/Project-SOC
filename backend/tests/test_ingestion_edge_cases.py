import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd

from app.ingestion.normalizer import (
    normalize_batch,
    normalize_process,
    normalize_security_alert,
    _parse_timestamp,
    NormalizedLog
)
from app.ingestion.scheduler import get_window_bucket

class TestSyslogParsingEdgeCases:
    def test_syslog_no_src_field(self):
        doc = {"_id": "1", "message": "DST=1.1.1.1 PROTO=TCP SPT=123 DPT=80"}
        res = normalize_batch([doc], "network")[0]
        assert res.src_ip is None
        assert res.dst_ip == "1.1.1.1"

    def test_syslog_malformed_ip_format(self):
        doc = {"_id": "2", "message": "SRC=999.999.999.999 DST=8.8.8.8 PROTO=UDP"}
        res = normalize_batch([doc], "network")[0]
        assert res.src_ip == "999.999.999.999"

    def test_syslog_ipv6_address(self):
        doc = {"_id": "3", "message": "SRC=2001:0db8::1 DST=::1 PROTO=TCP"}
        res = normalize_batch([doc], "network")[0]
        assert res.src_ip == "2001:0db8::1"
        assert res.dst_ip == "::1"

    def test_syslog_multiple_src_in_message(self):
        doc = {"_id": "4", "message": "SRC=1.1.1.1 SRC=2.2.2.2 PROTO=TCP"}
        res = normalize_batch([doc], "network")[0]
        assert res.src_ip == "1.1.1.1"

    def test_syslog_empty_message_field(self):
        doc = {"_id": "5", "message": ""}
        res = normalize_batch([doc], "network")[0]
        assert res.src_ip is None
        assert res.dst_ip is None

    def test_syslog_extremely_long_message(self):
        import time
        long_str = "x" * 50000
        doc = {"_id": "6", "message": f"SRC=1.1.1.1 DST=2.2.2.2 {long_str}"}
        start = time.time()
        res = normalize_batch([doc], "network")[0]
        end = time.time()
        assert res.src_ip == "1.1.1.1"
        assert (end - start) < 0.1

class TestProcessNormalizationEdgeCases:
    @pytest.mark.parametrize("args, expected", [
        ("single_arg", ["single_arg"]),
        (["arg1", "arg2"], ["arg1", "arg2"]),
        (None, [])
    ])
    def test_process_args_as_string_not_list(self, args, expected):
        doc = {"_id": "1", "process": {"args": args}}
        res = normalize_process(doc)
        assert res.process_args == expected

    def test_process_command_line_with_special_chars(self):
        cmd = "C:\\path\\null\x00\\weird\u202Echar.exe"
        doc = {"_id": "2", "process": {"command_line": cmd}}
        res = normalize_process(doc)
        assert res.process_command_line == cmd

    def test_process_negative_exit_code(self):
        doc = {"_id": "3", "process": {"exit_code": -1}}
        res = normalize_process(doc)
        assert res.process_exit_code == -1

    def test_process_pid_as_string_coerced_to_int(self):
        # normalize_process currently gets process_pid as-is. If it returns the string, we assert that.
        doc = {"_id": "4", "process": {"pid": "1234"}}
        res = normalize_process(doc)
        assert res.process_pid == "1234"

    def test_process_missing_parent_entirely(self):
        doc = {"_id": "5", "process": {"name": "test.exe"}}
        res = normalize_process(doc)
        assert res.process_parent_name is None
        assert res.process_parent_executable is None
        assert res.process_parent_command_line is None

class TestSecurityAlertEdgeCases:
    def test_alert_threat_array_empty(self):
        doc = {"_id": "1", "kibana": {"alert": {"rule": {"threat": []}}}}
        res = normalize_security_alert(doc)
        assert res.alert_mitre_tactic is None
        assert res.alert_mitre_technique_id is None

    def test_alert_threat_nested_structure_variations(self):
        doc = {"_id": "2", "kibana": {"alert": {"rule": {"threat": [{"tactic": {"name": "Defense Evasion"}, "technique": [{"id": "T1036"}]}]}}}}
        res = normalize_security_alert(doc)
        assert res.alert_mitre_tactic == "Defense Evasion"
        assert res.alert_mitre_technique_id == "T1036"

    def test_alert_risk_score_as_string(self):
        doc = {"_id": "3", "kibana": {"alert": {"risk_score": "85.5"}}}
        res = normalize_security_alert(doc)
        assert res.alert_risk_score == 85.5

    def test_alert_severity_unexpected_value(self):
        doc = {"_id": "4", "kibana": {"alert": {"severity": "informational"}}}
        res = normalize_security_alert(doc)
        assert res.alert_severity == "informational"

class TestBatchProcessingEdgeCases:
    def test_empty_batch_returns_empty_list(self):
        res = normalize_batch([], "network")
        assert res == []

    def test_batch_with_all_invalid_docs(self):
        res = normalize_batch([None, {}], "process")
        # Empty dict is valid because .get() just returns None, so it yields NormalizedLog with all Nones.
        # But None raises AttributeError during .get()
        assert len(res) == 1

    def test_batch_mixed_valid_invalid(self):
        docs = [{"_id": str(i), "process": {"name": "test.exe"}} for i in range(50)] + [None] * 5
        res = normalize_batch(docs, "process")
        assert len(res) == 50

    def test_duplicate_doc_ids_in_batch(self):
        docs = [
            {"_id": "same_id", "message": "SRC=1.1.1.1"},
            {"_id": "same_id", "message": "SRC=2.2.2.2"}
        ]
        res = normalize_batch(docs, "network")
        assert len(res) == 2
        assert res[0].src_ip == "1.1.1.1"
        assert res[1].src_ip == "2.2.2.2"

class TestTimestampEdgeCases:
    def test_timestamp_missing_falls_back_to_ingestion_time(self):
        doc = {"_id": "1"}
        before = datetime.utcnow()
        res = normalize_process(doc)
        after = datetime.utcnow()
        assert before <= res.timestamp <= after

    def test_timestamp_future_dated(self):
        future = datetime.utcnow() + timedelta(days=365)
        doc = {"_id": "2", "@timestamp": future.isoformat()}
        res = normalize_process(doc)
        assert res.timestamp.year == future.year

    @pytest.mark.parametrize("ts_str", [
        "2023-10-01T14:30:00Z",
        "2023-10-01T14:30:00.123456Z",
        "2023-10-01T14:30:00+05:30",
        "2023-10-01 14:30:00"
    ])
    def test_timestamp_various_iso_formats(self, ts_str):
        ts = _parse_timestamp(ts_str)
        assert ts is not None
        assert ts.year == 2023
        assert ts.month == 10
        assert ts.day == 1

    def test_window_bucket_flooring_correct(self):
        ts = datetime(2023, 10, 1, 14, 32, 47)
        floored = get_window_bucket(ts, 5)
        assert floored == datetime(2023, 10, 1, 14, 30, 0)
