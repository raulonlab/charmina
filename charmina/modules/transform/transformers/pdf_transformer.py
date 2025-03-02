import os
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser

from charmina.modules.dataclasses import TransformConfig


class PdfTransformer:
    """Default transformer.

    Args:
        file_path: Path to the file to load.
    """

    file_path: str
    config_parser: ConfigParser

    def __init__(
        self,
        file_path: str,
        transform_config: TransformConfig = TransformConfig(),
    ):
        """Initialize with file path."""
        self.file_path = file_path

        self.config_parser = ConfigParser(
            {
                "langugages": "en",
                "page_range": transform_config.page_range,
                "output_format": "markdown",  # [markdown|json|html]
                "output_dir": None,
                # "max_pages": self.max_pages,
                # "batch_multiplier": self.batch_multiplier,
                # "start_page": self.start_page,
                # "force_overwrite": self.force_overwrite,
                "force_ocr": False,
                "disable_image_extraction": True,
                "disable_multiprocessing": True,
                # "disable_tqdm": True,
                "use_llm": False,
                # "llm_service": "marker.services.gemini.GoogleGeminiService",
                "disable_links": False,
                "paginate_output": False,
                # "page_separator": "------------------",
            }
        )

    def transform(self) -> str:
        """Transform source file path."""
        if not os.path.exists(self.file_path):
            raise ValueError(f"Input file path does not exist: {self.file_path}")

        converter = PdfConverter(
            config=self.config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=self.config_parser.get_processors(),
            renderer=self.config_parser.get_renderer(),
            # llm_service=self.config_parser.get_llm_service()
        )
        rendered = converter(self.file_path)
        output_text, _, images = text_from_rendered(rendered)
        # output_metadata = rendered.metadata or {}

        return output_text
