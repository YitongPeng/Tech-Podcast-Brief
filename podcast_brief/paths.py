from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import DATA_DIR_NAME


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def data_dir(self) -> Path:
        return self.root / DATA_DIR_NAME

    @property
    def db_path(self) -> Path:
        return self.data_dir / "episodes.sqlite"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def transcripts_dir(self) -> Path:
        return self.data_dir / "transcripts"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def episode_outputs_dir(self) -> Path:
        return self.outputs_dir / "episodes"

    @property
    def daily_brief_dir(self) -> Path:
        return self.outputs_dir / "daily_brief"


def get_project_paths() -> ProjectPaths:
    # Project root = directory that contains this package's parent.
    root = Path(__file__).resolve().parents[1]
    return ProjectPaths(root=root)

