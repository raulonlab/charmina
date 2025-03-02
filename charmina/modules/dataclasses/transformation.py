# from __future__ import annotations

import os
from typing import List
from dataclasses import dataclass
from datafiles import datafile, formats, field


TRANSFORM_FILE_EXTENSION = ".transform.yml"
formats.register(TRANSFORM_FILE_EXTENSION, formats.YAML)


@dataclass
class Transformation:
    chunks: List[str] = field(default_factory=list)


@datafile(
    f"{{self.source_path}}{TRANSFORM_FILE_EXTENSION}", manual=True, defaults=False
)
@dataclass(kw_only=True)
class TransformationDataFile(Transformation):
    source_path: str

    def __post_init__(self):
        # Convert to absolute path (avoid issues with datafile pattern and relative paths)
        # Remove duplicated extension if necessary
        self.source_path = os.path.abspath(
            self.source_path[: -len(TRANSFORM_FILE_EXTENSION)]
            if self.source_path.endswith(TRANSFORM_FILE_EXTENSION)
            else self.source_path
        )
