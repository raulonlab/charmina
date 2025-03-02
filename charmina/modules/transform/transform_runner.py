import os
from pathlib import Path
import glob
import logging
from time import sleep
from typing import Any, Dict, Iterable, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from charmina.libs.event_emitter import EventEmitter
from charmina.libs.helpers import replace_file_path_root
from charmina.modules.dataclasses import MetadataDataFile, TransformationDataFile
from charmina.modules.transform.transformers import (
    BypassTransformer,
    PdfTransformer,
    Mp3Transformer,
)


_RUN_TASKS_LIMIT = 1_000  # Maximum number of tasks to run in a single call to run()
_MAX_WORKERS = (
    1  # 4 if os.cpu_count() > 4 else 2  # Maximum number of workers to run in parallel
)


# Map file extensions to metadata loaders and their arguments
_TRANSFORMER_MAPPING = {
    ".mp3": (Mp3Transformer, {}),
    ".mp4": (Mp3Transformer, {}),
    ".pdf": (PdfTransformer, {}),
    ".txt": (BypassTransformer, {}),
    ".md": (BypassTransformer, {}),
    # Add more mappings for other file extensions and loaders as needed
}


class TransformRunner(EventEmitter):
    def __init__(self, **_kwconfig):
        super().__init__()

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
        logging.debug("Starting transform runner...")

        if not source_files and not source_directory:
            raise ValueError("No source files or directory provided")

        elif source_directory:
            logging.debug("Finding meta files...")
            source_files = TransformRunner.ifind_source_files(source_directory)

            # Sort reverse files to process the most recent first
            # meta_files = sorted(meta_files, reverse=True)

        missing_output_directories = set()
        transform_file_arguments = []
        for source_file in source_files:
            # Filter out files that don't match the search pattern
            if file_search_pattern and file_search_pattern not in source_file:
                continue

            # Load metadata file and check if it exists
            metadata_file = MetadataDataFile(source_path=source_file)
            if not metadata_file.datafile.exists:
                logging.warning(f"Metadata file not found: {source_file}")

            # Locate output transformation file and check if it exists
            output_source_path = replace_file_path_root(
                file_path=metadata_file.source_path,
                input_root_path=source_root_path,
                output_root_path=output_root_path,
            )
            transform_file = TransformationDataFile(source_path=output_source_path)

            if not overwrite and transform_file.datafile.exists:
                logging.debug(
                    f"Transformation file already exists: {transform_file.datafile.path}"
                )
                continue

            transform_file_arguments.append(
                {
                    "input_meta_source_path": metadata_file.source_path,
                    "output_transform_source_path": transform_file.source_path,
                }
            )

            # Add missing output directories
            missing_output_directories.add(os.path.dirname(transform_file.source_path))

        # Return dry run result
        if dry_run == True:
            return [
                argument["output_transform_source_path"]
                for argument in transform_file_arguments
            ], []

        # Return if no files to transform
        if len(transform_file_arguments) == 0:
            logging.debug("No source files to transform")
            return [], []

        # Create missing output directories
        for missing_output_directory in missing_output_directories:
            os.makedirs(missing_output_directory, exist_ok=True)

        # Limit number of tasks to run
        if not limit or not 0 < limit < _RUN_TASKS_LIMIT:
            limit = _RUN_TASKS_LIMIT
        if len(transform_file_arguments) > limit:
            logging.warning(
                f"Number of files to transform cut to limit {limit} (out of {len(transform_file_arguments)})"
            )
            transform_file_arguments = transform_file_arguments[:limit]

        logging.debug(f"Start transforming {len(transform_file_arguments)} files...")

        # Emit start event (show progress bar in UI)
        self.emit("start", len(transform_file_arguments))

        results = []
        errors = []
        with ProcessPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            response_futures = [
                executor.submit(TransformRunner.transform_file, transform_argument)
                for transform_argument in transform_file_arguments
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

    @staticmethod
    def transform_file(input_arguments: Dict[str, Any]) -> str:
        input_meta_source_path = input_arguments["input_meta_source_path"]
        output_transform_source_path = input_arguments["output_transform_source_path"]

        input_meta_source_abs_path = str(Path(input_meta_source_path).resolve())
        if not os.path.exists(input_meta_source_abs_path):
            raise FileNotFoundError(f"File not found {input_meta_source_abs_path}")

        output_transform_source_abs_path = str(
            Path(output_transform_source_path).resolve()
        )

        # Run transformer based on the file extension
        ext = "." + input_meta_source_path.rsplit(".", 1)[-1]
        if ext in _TRANSFORMER_MAPPING:
            # Load metadata of input file
            try:
                metadata_file = MetadataDataFile(source_path=input_meta_source_abs_path)
            except Exception as e:
                raise Exception(
                    f"Error loading metadata for '{input_meta_source_path}'"
                ) from e

            # Transform input file
            try:
                transformer_class, transformer_args = _TRANSFORMER_MAPPING[ext]
                transformer = transformer_class(
                    file_path=input_meta_source_abs_path,
                    transform_config=metadata_file.transform_config,
                    **transformer_args,
                )
                transformer_output: str = transformer.transform()

                # Unblock system resources
                sleep(0.2)
            except Exception as e:
                raise Exception(
                    f"Error transforming file '{input_meta_source_path}'"
                ) from e

            # Create transformation output file
            try:
                transformation = TransformationDataFile(
                    source_path=output_transform_source_abs_path,
                    chunks=[
                        transformer_output
                    ],  # Issue: value is not set when underlying file exists
                )
                transformation.datafile.save()

                return transformation.datafile.path
            except Exception as e:
                raise Exception(
                    f"Error creating transformation file for '{input_meta_source_path}'"
                ) from e

    @staticmethod
    def ifind_source_files(directory_path: str) -> Iterable[str]:
        for ext, _ in _TRANSFORMER_MAPPING.items():
            for file_path in glob.iglob(
                os.path.join(directory_path, f"**/*{ext}"), recursive=True
            ):
                yield file_path
