import os
from pathlib import Path
import glob
import logging
from typing import Any, Dict, Iterable, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from charmina.libs.event_emitter import EventEmitter
from charmina.libs.helpers import replace_file_path_root
from charmina.modules.dataclasses import MetadataDataFile, TransformationDataFile
from charmina.modules.dataclasses.transformation import TRANSFORM_FILE_EXTENSION
from charmina.modules.scribe.scribers import (
    JinjaScriber,
)


_RUN_TASKS_LIMIT = 1_000  # Maximum number of tasks to run in a single call to run()
_MAX_WORKERS = 1
# (
#     4 if os.cpu_count() > 4 else 2
# )  # Maximum number of workers to run in parallel

# Map file extensions to metadata loaders and their arguments
_SCRIBER_TEMPLATE_MAPPING = {
    ".mp3": "audio_template",
    ".mp4": "audio_template",
    ".pdf": "document_template",
    ".txt": "document_template",
    ".md": "document_template",
}

_SCRIBER_OUTPUT_EXTENSION = ".md"


class ScribeRunner(EventEmitter):
    templates: Dict[str, str] = None

    def __init__(self, templates: Dict[str, str], **_kwconfig):
        super().__init__()

        self.templates = templates

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
        logging.debug("Starting scribe runner...")

        if not source_files and not source_directory:
            raise ValueError("No source files or directory provided")

        elif not source_files:
            logging.debug("Finding transform files...")
            transform_files = ScribeRunner.ifind_transform_files(source_directory)

            # Sort reverse files to process the most recent first
            # transform_files = sorted(transform_files, reverse=True)

        missing_output_directories = set()
        scriber_file_arguments = []
        for transform_file in transform_files:
            # Filter out files that don't match the search pattern
            if file_search_pattern and file_search_pattern not in transform_file:
                continue

            # Load metadata file and check if it exists
            transformation_datafile = TransformationDataFile(source_path=transform_file)
            if not transformation_datafile.datafile.exists:
                logging.warning(f"Transformation file not found: {transform_file}")
                continue

            # Locate output file and check if it exists
            output_source_path = replace_file_path_root(
                file_path=transformation_datafile.source_path,
                input_root_path=source_root_path,
                output_root_path=output_root_path,
            )

            if not overwrite:
                # Search for files in the parent directory that match the search pattern
                search_existing_pattern = (
                    glob.escape(os.path.splitext(output_source_path)[0]) + "_*.md"
                )
                # print("search_existing_pattern: ", search_existing_pattern)
                matching_existing_files = glob.glob(
                    search_existing_pattern, include_hidden=True
                )

                # print("matching_existing_files:\n", matching_existing_files)

                if matching_existing_files:
                    logging.debug(
                        f"Output scribe files already exists: {output_source_path}*"
                    )
                    continue

            scriber_file_arguments.append(
                {
                    "input_source_file_path": transformation_datafile.source_path,
                    "output_scribe_directory_path": os.path.dirname(output_source_path),
                }
            )

            # Add missing output directories
            missing_output_directories.add(
                scriber_file_arguments[-1]["output_scribe_directory_path"]
            )

        # Return dry run result
        if dry_run == True:
            return [
                argument["output_scribe_directory_path"]
                for argument in scriber_file_arguments
            ], []

        # Return if no files to scribe
        if len(scriber_file_arguments) == 0:
            logging.debug("No source files to scribe")
            return [], []

        # Create missing output directories
        for missing_output_directory in missing_output_directories:
            os.makedirs(missing_output_directory, exist_ok=True)

        # Limit number of tasks to run
        if not limit or not 0 < limit < _RUN_TASKS_LIMIT:
            limit = _RUN_TASKS_LIMIT
        if len(scriber_file_arguments) > limit:
            logging.warning(
                f"Number of files to scribe cut to limit {limit} (out of {len(scriber_file_arguments)})"
            )
            scriber_file_arguments = scriber_file_arguments[:limit]

        logging.debug(f"Start writing {len(scriber_file_arguments)} files...")

        # Emit start event (show progress bar in UI)
        self.emit("start", len(scriber_file_arguments))

        results = []
        errors = []
        with ThreadPoolExecutor(
            max_workers=_MAX_WORKERS, thread_name_prefix="ScribeRunner"
        ) as executor:
            response_futures = [
                executor.submit(self.scribe_file, scribe_file_argument)
                for scribe_file_argument in scriber_file_arguments
            ]

            for response_future in as_completed(response_futures):
                try:
                    response = response_future.result()
                    if response:
                        results.append(response)
                        self.emit(
                            "write",
                            (
                                str(response[0])
                                if isinstance(response, list)
                                else str(response)
                            ),
                        )
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

    def scribe_file(self, input_arguments: Dict[str, Any]) -> List[str]:
        input_source_file_path = input_arguments["input_source_file_path"]
        output_scribe_directory_path = input_arguments["output_scribe_directory_path"]

        # Load transform datafile of input file
        transform_datafile = TransformationDataFile(source_path=input_source_file_path)
        if not transform_datafile.datafile.exists:
            raise FileNotFoundError(
                f"Transformation file not found {input_source_file_path}"
            )

        # Load metadata datafile of input file
        metadata_datafile = MetadataDataFile(source_path=input_source_file_path)
        if not metadata_datafile.datafile.exists:
            raise FileNotFoundError(f"Metadata file not found {input_source_file_path}")

        # Input source file basename and ext
        input_source_file_basename, input_source_file_ext = os.path.splitext(
            os.path.basename(input_source_file_path)
        )

        # Get scribe template based on file extension
        scribe_template = _SCRIBER_TEMPLATE_MAPPING.get(
            str(input_source_file_ext).lower(), None
        )
        if not scribe_template:
            raise ValueError(f"No scribe template found for '{input_source_file_ext}'")

        # Scribe output
        jinja_scriber = JinjaScriber(
            transformation=transform_datafile,
            metadata=metadata_datafile.metadata,
            template_string=self.templates.get(scribe_template, None),
        )

        scriber_outputs = jinja_scriber.scribe()

        output_scribe_chunk_file_paths = []
        try:
            # Write output chunk files
            for index, scriber_chunk_output in enumerate(scriber_outputs):
                output_scribe_chunk_file_path = Path(
                    output_scribe_directory_path,
                    f"{input_source_file_basename}_{index + 1}{_SCRIBER_OUTPUT_EXTENSION}",
                )
                with open(output_scribe_chunk_file_path, "w") as output_file:
                    output_file.write(scriber_chunk_output)

                output_scribe_chunk_file_paths.append(output_scribe_chunk_file_path)

        except Exception as e:
            raise Exception(
                f"Error writing scribe file for '{input_source_file_path}'"
            ) from e

        return output_scribe_chunk_file_paths

    @staticmethod
    def ifind_transform_files(directory_path: str) -> Iterable[str]:
        for file_path in glob.iglob(
            os.path.join(directory_path, f"**/*{TRANSFORM_FILE_EXTENSION}"),
            recursive=True,
        ):
            yield file_path
