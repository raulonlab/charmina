# Description: Mp3 scriber.

from typing import List
import jinja2
from charmina.modules.dataclasses import Metadata, Transformation


class JinjaScriber:
    """Jinja scriber.


    Args:
        transform_datafile: transform datafile.
    """

    transformation: Transformation
    metadata: Metadata
    template: jinja2.environment.Template

    def __init__(
        self,
        transformation: Transformation,
        metadata: Metadata,
        template_string: str,
    ):
        if not template_string or not str(template_string).strip():
            raise ValueError("A non empty template is required")

        environment = jinja2.Environment(
            keep_trailing_newline=True, trim_blocks=True
        )  # keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True
        self.template = environment.from_string(template_string)

        self.transformation = transformation
        self.metadata = metadata

    def scribe(self) -> List[str]:
        """Scribe transformed datafile file in output format."""

        metadata_dict = self.metadata.get_front_matter_ready_dict()
        rendered_chunks = []
        for chunk in self.transformation.chunks:
            rendered_chunk = self.template.render(chunk=chunk, metadata=metadata_dict)
            rendered_chunks.append(rendered_chunk)

        return rendered_chunks
