import os
import glob
import logging
from typing import Iterable, List, Tuple, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from charmina.libs.event_emitter import EventEmitter
from charmina.libs.helpers import sanitize_text, replace_file_path_root
from charmina.modules.dataclasses import Metadata, MetadataDataFile
from charmina.modules.extract.meta_extractors import (
    DefaultMetaExtractor,
    Mp3MetaExtractor,
)
from charmina.modules.llm.llm import LLM

_RUN_TASKS_LIMIT = 1_000  # Maximum number of tasks to run in a single call to run()
_MAX_WORKERS = (
    4 if os.cpu_count() > 4 else 2
)  # Maximum number of workers to run in parallel


# Map file extensions to extract runners and their arguments
_META_EXTRACTOR_MAPPING = {
    ".mp3": (Mp3MetaExtractor, {}),
    ".mp4": (Mp3MetaExtractor, {}),
    ".pdf": (DefaultMetaExtractor, {}),
    ".txt": (DefaultMetaExtractor, {}),
    ".md": (DefaultMetaExtractor, {}),
    # Add more mappings for other file extensions and meta_extractors as needed
}


class ExtractRunner(EventEmitter):
    llm_config: Dict[str, Any] = None
    use_llm_refine_description: bool = False

    def __init__(
        self,
        use_llm_refine_description: bool = False,
        prompts: Dict[str, str] = None,
        openai: Dict[str, str] = None,
        **_kwconfig,
    ):
        super().__init__()

        if (use_llm_refine_description) and not (prompts or openai):
            raise ValueError("LLM prompts and OpenAI API key must be provided")

        self.use_llm_refine_description = use_llm_refine_description
        self.prompts = prompts
        self.openai = openai

    def run(
        self,
        source_directory: str = ".",
        source_files: List[str] = None,
        source_root_path: str = None,
        output_root_path: str = None,
        file_search_pattern: str = None,
        overwrite: bool = False,
        dry_run: bool = False,
        limit: int = _RUN_TASKS_LIMIT,
    ) -> Tuple[List[str], List[any]]:
        logging.debug("Starting extract runner...")

        if not source_files and not source_directory:
            raise ValueError("No source files or directory provided")

        elif not source_files:
            logging.debug("Finding source files...")
            source_files = ExtractRunner.ifind_source_files(source_directory)

            # Sort reverse files to process the most recent first
            # source_files = sorted(source_files, reverse=True)

        missing_output_directories = set()
        extract_file_arguments = []
        for source_file in source_files:
            # Filter out files that don't match the search pattern
            if file_search_pattern and file_search_pattern not in source_file:
                continue

            # Locate output file and check if it exists
            output_source_path = replace_file_path_root(
                file_path=source_file,
                input_root_path=source_root_path,
                output_root_path=output_root_path,
            )

            # Load metadata file and check if it exists
            metadata_file = MetadataDataFile(source_path=output_source_path)
            if not overwrite and metadata_file.datafile.exists:
                logging.debug(
                    f"Metadata file already exists: {metadata_file.datafile.path}"
                )
                continue

            extract_file_arguments.append(
                {
                    "input_source_file_path": source_file,
                    "output_directory_path": os.path.dirname(output_source_path),
                }
            )

            # Add missing output directories
            missing_output_directories.add(
                extract_file_arguments[-1]["output_directory_path"]
            )

        # Return dry run result
        if dry_run == True:
            return [
                argument["output_directory_path"] for argument in extract_file_arguments
            ], []

        # Return if no files to process
        if len(extract_file_arguments) == 0:
            logging.debug("No source files to extract")
            return [], []

        # Create missing output directories
        for missing_output_directory in missing_output_directories:
            os.makedirs(missing_output_directory, exist_ok=True)

        # Limit number of tasks to run
        if not limit or not 0 < limit < _RUN_TASKS_LIMIT:
            limit = _RUN_TASKS_LIMIT
        if len(extract_file_arguments) > limit:
            logging.warning(
                f"Number of files to extract cut to limit {limit} (out of {len(extract_file_arguments)})"
            )
            extract_file_arguments = extract_file_arguments[:limit]

        logging.debug(f"Start extracting {len(extract_file_arguments)} files...")

        # Emit start event (show progress bar in UI)
        self.emit("start", len(extract_file_arguments))

        results = []
        errors = []
        with ThreadPoolExecutor(
            max_workers=_MAX_WORKERS, thread_name_prefix="ExtractRunner"
        ) as executor:
            response_futures = [
                executor.submit(self.extract_file, **extract_file_argument)
                for extract_file_argument in extract_file_arguments
            ]

            for response_future in as_completed(response_futures):
                try:
                    response = response_future.result()
                    if response:
                        results.append(response)
                        self.emit("write", str(response))
                    else:
                        self.emit("write", "")
                except Exception as err:
                    errors.append(err)
                    self.emit("write", str(err), is_error=True)
                    continue
                finally:
                    self.emit("update")

        self.emit("close")
        return results, errors

    def extract_file(
        self, input_source_file_path: str, output_directory_path: str | None
    ) -> str | None:
        if not os.path.exists(input_source_file_path):
            raise FileNotFoundError(f"File not found {input_source_file_path}")

        if not output_directory_path:
            output_directory_path = os.path.dirname(input_source_file_path)

        # Input source file basename and ext
        input_source_file_basename, input_source_file_ext = os.path.splitext(
            os.path.basename(input_source_file_path)
        )

        # Get extractor class and args based on the file extension
        meta_extractor_class, meta_extractor_args = _META_EXTRACTOR_MAPPING.get(
            input_source_file_ext, (None, {})
        )

        if not meta_extractor_class:
            raise Exception(
                f"No metadata extractor found for extention '{input_source_file_ext}' of '{input_source_file_path}'"
            )

        try:
            meta_extractor = meta_extractor_class(
                source_path=input_source_file_path, **meta_extractor_args
            )
            metadata_dict = meta_extractor.extract()

            metadata_file = MetadataDataFile(
                source_path=os.path.join(
                    output_directory_path,
                    f"{input_source_file_basename}{input_source_file_ext}",
                ),
                metadata=Metadata(**metadata_dict),
            )

            # Sanatize (Remove special characters)
            metadata_file.metadata.title = sanitize_text(metadata_file.metadata.title)
            metadata_file.metadata.description = sanitize_text(
                metadata_file.metadata.description
            )

            # Refine description (Clean up, remove timestamps, links, and promotional content, etc)
            if self.use_llm_refine_description and metadata_file.metadata.description:
                llm = LLM(prompts=self.prompts, **self.openai)
                refined_description = llm.refine_text(
                    text=metadata_file.metadata.description,
                    context=metadata_file.metadata.title,
                )

                metadata_file.metadata.description = refined_description

            metadata_file.datafile.save()

            return metadata_file.datafile.path
        except Exception as e:
            raise Exception(
                f"Error extracting source file '{input_source_file_path}'"
            ) from e

    @staticmethod
    def ifind_source_files(directory_path: str) -> Iterable[str]:
        for ext, _ in _META_EXTRACTOR_MAPPING.items():
            for file_path in glob.iglob(
                os.path.join(directory_path, f"**/*{ext}"), recursive=True
            ):
                yield file_path
