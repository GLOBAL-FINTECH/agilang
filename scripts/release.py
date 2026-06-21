"""Create AGILANG release archives after validation."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
RELEASE.mkdir(exist_ok=True)
version = "0.6.0"
archive_base = RELEASE / f"AGILANG_v{version.replace('.', '_')}_source"
zip_path = shutil.make_archive(str(archive_base), "zip", ROOT)
print(f"Created {zip_path}")
