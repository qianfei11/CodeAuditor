"""Configuration dataclasses for the protocol auditor."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuditConfig:
    target: str
    output_dir: str
    skill_dir: str  # path to audit-network-protocol/
    max_parallel: int = 4
    threat_model: str = (
        "Network attacker with full control over protocol messages. "
        "The attacker can send arbitrary bytes, malformed messages, "
        "and exploit any parsing or handling vulnerability."
    )
    scope: str = ""
    skip_stages: list[int] = field(default_factory=list)
    resume: bool = False


@dataclass
class Module:
    id: str          # e.g., "M-1"
    name: str
    description: str
    files_dir: str
    analyze: bool


@dataclass
class EntryPoint:
    id: str          # e.g., "EP-1"
    module_id: str   # e.g., "M-1"
    type: str        # "P", "H", or "S"
    module_name: str
    location: str
    attacker_controlled_data: str
    initial_validation: str
    analysis_hints: str
    raw_block: str   # full markdown block for the EP


@dataclass
class PendingFinding:
    """A Stage 4 pending finding awaiting ID assignment."""
    stage3_filename: str      # e.g., "M-1-EP-3-F-01.md"
    pending_path: str         # path to _pending/{stage3_filename}
    severity: str             # Critical / High / Medium / Low
    global_id: Optional[str] = None   # e.g., "C-01", assigned after evaluation
