from __future__ import annotations

import json
import os
import tempfile

from code_auditor.parsing.stage3 import parse_au_file
from code_auditor.report.generate import generate_report
from code_auditor.validation.stage3 import validate_stage3_file
from code_auditor.validation.stage5 import validate_stage5_file


def test_stage3_parser_reads_single_au_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "M-1-1.json")
        with open(path, "w") as f:
            json.dump({
                "description": "Parses raw DHCP packets from the network",
                "files": ["src/parser/parse.c", "src/parser/options.c"],
                "focus": "Trace the len field from the packet header through parse_options().",
            }, f)

        unit = parse_au_file(path)
        assert unit.description == "Parses raw DHCP packets from the network"
        assert len(unit.files) == 2
        assert validate_stage3_file(path) == []


def test_stage3_validator_rejects_empty_fields():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "M-2-1.json")
        with open(path, "w") as f:
            json.dump({"description": "", "files": [], "focus": ""}, f)

        issues = validate_stage3_file(path)
        assert len(issues) == 3  # description, files, focus all blank


def test_stage5_validator_and_report_generator_accept_json():
    with tempfile.TemporaryDirectory() as tmp:
        stage1_dir = os.path.join(tmp, "stage-1-details")
        os.makedirs(stage1_dir)
        research_record_path = os.path.join(stage1_dir, "stage-1-security-context.json")
        stage5_dir = os.path.join(tmp, "stage-5-details")
        report_path = os.path.join(tmp, "report.md")
        finding_path = os.path.join(stage5_dir, "H-01.json")

        os.makedirs(stage5_dir)
        with open(research_record_path, "w") as f:
            json.dump({
                "project": {
                    "name": "Example Protocol",
                    "path": "/tmp/example",
                    "language": "C",
                    "description": "Example protocol implementation.",
                    "deployment_model": "Network daemon",
                },
                "sources_consulted": [],
                "scope_announcements": {
                    "in_scope_modules": [],
                    "out_of_scope_modules": [],
                    "in_scope_issue_types": ["memory corruption"],
                    "out_of_scope_issue_types": ["test code"],
                },
                "historical_vulnerabilities": [
                    {
                        "cve_id": "CVE-2024-1234",
                        "date": "2024-01-15",
                        "affected_component": "parser",
                        "vulnerability_class": "buffer overflow",
                        "root_cause": "Missing bounds check",
                        "impact": "RCE",
                        "severity": "Critical",
                        "attacker_profile": "Network attacker",
                        "summary": "Heap buffer overflow in protocol parser.",
                    },
                ],
                "severity_guidance": {
                    "source": "SECURITY.md",
                    "raw_quotes": [],
                    "notes": "Memory corruption in parsers is Critical.",
                },
                "fuzzing_targets": [],
                "notes": "",
            }, f)
        with open(finding_path, "w") as f:
            json.dump({
                "id": "H-01",
                "title": "Length underflow reaches memcpy",
                "location": "src/parser.c:parse_packet (lines 10-24)",
                "cwe_id": ["CWE-191"],
                "vulnerability_class": ["integer underflow"],
                "cvss_score": "8.1",
                "severity": "High",
                "prerequisites": "Default configuration",
                "impact": "DoS",
                "code_snippet": "memcpy(...)",
            }, f)

        assert validate_stage5_file(finding_path) == []

        summary = generate_report(research_record_path, stage5_dir, report_path)
        report_content = open(report_path).read()

        assert summary.total_findings == 1
        assert "H-01: Length underflow reaches memcpy" in report_content
        assert "Example Protocol" in report_content
        assert "CVE-2024-1234" in report_content
