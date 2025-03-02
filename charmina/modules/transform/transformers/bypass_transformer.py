import os


class BypassTransformer:
    """ByPass transformer. Return the text content of the file.

    Args:
        file_path: Path to the file to load.
    """

    file_path: str

    def __init__(
        self,
        file_path: str,
    ):
        """Initialize with file path."""
        self.file_path = file_path

    def transform(self) -> str:
        """Transform source file path."""
        if not os.path.exists(self.file_path):
            raise ValueError(f"Input file path does not exist: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as file:
            return file.read()
