import json
from typing import Dict, Any
import music_tag


class Mp3MetaExtractor:
    """Load metadata from mp3 file tags.


    Args:
        source_path: Path to source file to load.
    """

    def __init__(
        self,
        source_path: str,
    ):
        """Initialize with file path."""
        self.source_path = source_path

    def extract(self) -> Dict[str, Any]:
        """Load from file path."""
        music_tag_file = music_tag.load_file(self.source_path)

        # Load metadata from 'comment' tag
        metadata = None
        try:
            comment_metadata_str = str(music_tag_file["comment"])
            if comment_metadata_str:
                metadata = json.loads(comment_metadata_str)

            if not metadata:
                metadata = {}

        except:
            metadata = {}

        if not metadata.get("author", None):
            metadata["author"] = str(music_tag_file["artist"]) or ""
        if not metadata.get("title", None):
            metadata["title"] = str(music_tag_file["title"]) or ""
        if not metadata.get("album", None):
            metadata["album"] = str(music_tag_file["album"]) or ""

        return metadata
