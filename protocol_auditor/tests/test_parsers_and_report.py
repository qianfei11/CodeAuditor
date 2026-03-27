from __future__ import annotations

import json
import os
import tempfile

from protocol_auditor.parsing.stage2 import parse_au_file
from protocol_auditor.report.generate import generate_report
from protocol_auditor.validation.stage2 import validate_stage2_file
from protocol_auditor.validation.stage5 import validate_stage5_file


def test_stage2_parser_reads_single_au_file():
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
        assert validate_stage2_file(path) == []


def test_stage2_validator_rejects_empty_fields():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "M-2-1.json")
        with open(path, "w") as f:
            json.dump({"description": "", "files": [], "focus": ""}, f)

        issues = validate_stage2_file(path)
        assert len(issues) == 3  # description, files, focus all blank


def test_stage5_validator_and_report_generator_accept_json():
    with tempfile.TemporaryDirectory() as tmp:
        stage4_path = os.path.join(tmp, "stage-4-security-context.md")
        stage5_dir = os.path.join(tmp, "stage-5-details")
        report_path = os.path.join(tmp, "report.md")
        finding_path = os.path.join(stage5_dir, "H-01.json")

        os.makedirs(stage5_dir)
        with open(stage4_path, "w") as f:
            f.write(
                "# Security Context\n\n"
                "## Project Summary\n\n"
                "Example protocol implementation.\n\n"
                "## Attacker Profile\n\n"
                "Network attacker.\n\n"
                "## Attack Surface\n\n"
                "Protocol parser accepts untrusted input.\n\n"
                "## Vulnerability Patterns\n\n"
                "Memory corruption in parsers.\n"
            )
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

        summary = generate_report(stage4_path, stage5_dir, report_path)
        report_content = open(report_path).read()

        assert summary.total_findings == 1
        assert "H-01: Length underflow reaches memcpy" in report_content
