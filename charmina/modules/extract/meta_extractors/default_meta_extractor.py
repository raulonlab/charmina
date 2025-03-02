from typing import Dict, Any


class DefaultMetaExtractor:
    """Creates metadata file with default values.


    Args:
        file_path: file_path: Path to source file to load.
    """

    def __init__(
        self,
        source_path: str,
    ):
        """Initialize with file path."""
        self.source_path = source_path

    def extract(self) -> Dict[str, Any]:
        """Load from file path."""
        return {}
