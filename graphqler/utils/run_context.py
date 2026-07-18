from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from graphqler.config import RunSettings
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats


@dataclass
class RunContext:
    """Mutable state and immutable settings owned by one fuzzing run."""

    output_path: Path
    settings: RunSettings
    stats: Stats
    objects_bucket: ObjectsBucket
