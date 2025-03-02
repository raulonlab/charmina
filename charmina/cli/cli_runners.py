import logging
from pathlib import Path
import typer
from charmina.libs.enums import LogColors
from charmina.config import Config
from charmina.libs.helpers import get_filtered_directories
from charmina.cli import cli_utils


_global_config = Config.instance()

app = typer.Typer()


@app.command(
    "download",
    help="Download audio files (.mp3) of the youtube and podcast sources",
)
def run_download_command(
    source: cli_utils.DownloadSourceOption = None, limit: cli_utils.LimitOption = None
):
    cli_utils.validate_confirm_active_project()

    try:
        if not source or source == cli_utils.DownloadSourceEnum.youtube:
            # Module local import (speed up CLI start time)
            from charmina.libs.youtube_downloader import YoutubeDownloader

            youtube_downloader = YoutubeDownloader(
                source_urls=_global_config.get_project_youtube_sources(),
                config=_global_config,
            )

            typer.echo(
                f"\nDownloading audios from {LogColors.HIGHLIGHT}Yotube{LogColors.ENDC}"
            )
            tqdm_holder = cli_utils.TqdmHolder(desc="Completed", ncols=80)
            youtube_downloader.on("start", tqdm_holder.start)
            youtube_downloader.on("update", tqdm_holder.update)
            youtube_downloader.on("close", tqdm_holder.close)

            results, errors = youtube_downloader.run(
                output_path=str(
                    Path(
                        _global_config.get_project_base_path(),
                        Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
                        "youtube",
                    )
                ),
                limit=limit,
            )

            tqdm_holder.close()
            typer.echo(
                f"\n{len(results)} youtube audio files downloaded successfully with {len(errors)} errors...."
            )

            if len(errors) > 0:
                logging.error(
                    "Errors occurred while downloading audio files from youtube sources. Last error:\n",
                    exc_info=errors[-1],
                )

        if not source or source == cli_utils.DownloadSourceEnum.podcasts:
            # Module local import (speed up CLI start time)
            from charmina.libs.podcast_downloader import PodcastDownloader

            podcast_downloader = PodcastDownloader(
                feeds=_global_config.get_project_podcast_sources(),
                config=_global_config,
            )

            typer.echo(
                f"\nDownloading audios from {LogColors.HIGHLIGHT}Podcasts{LogColors.ENDC}"
            )
            podcast_downloader.run(
                output_path=str(
                    Path(
                        _global_config.get_project_base_path(),
                        Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
                        "podcasts",
                    )
                )
            )

            typer.echo("\nPodcast audio files downloaded successfully....")
    except Exception as e:
        logging.error("Error downloading audios from sources")
        raise e
    except SystemExit:
        raise typer.Abort()


@app.command(
    "extract",
    help="Create metadata files (.meta.yml) of the source files in `source` directory",
)
def run_extract_command(
    directory_filter: cli_utils.DirectoryFilterArgument = None,
    # file_search_pattern: cli_utils.FileFilterArgument = None,
    dry_run: cli_utils.DryRunOption = False,
    limit: cli_utils.LimitOption = None,
    overwrite: cli_utils.OverwriteOption = False,
):
    cli_utils.validate_confirm_active_project()

    try:
        project_source_documents_path = Path(
            _global_config.get_project_base_path(),
            Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
        )

        source_directories = get_filtered_directories(
            directory_filter=directory_filter,
            base_path=project_source_documents_path,
        )

        if not source_directories:
            logging.warning(
                f"No source directories found matching the filter '{directory_filter}'"
            )
            return

        # Module local import (speed up CLI start time)
        from charmina.modules.extract.extract_runner import ExtractRunner

        project_config = _global_config.get_project_config()
        runner = ExtractRunner(
            prompts=project_config["prompts"],
            openai=project_config["openai"],
            **project_config["extract"],
        )

        for source_directory in source_directories:
            typer.echo(
                f"\nExtracting {LogColors.URL}{source_directory}{LogColors.ENDC}"
            )
            tqdm_holder = cli_utils.TqdmHolder(desc="Completed", ncols=80)
            runner.on("start", tqdm_holder.start)
            runner.on("update", tqdm_holder.update)
            runner.on("write", tqdm_holder.write)
            runner.on("close", tqdm_holder.close)

            results, errors = runner.run(
                source_directory=str(source_directory),
                source_root_path=Path(
                    _global_config.get_project_base_path(),
                    Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
                ),
                dry_run=dry_run,
                limit=limit,
                overwrite=overwrite,
            )

            tqdm_holder.close()
            typer.echo(
                f"\n{'[Dry run] ' if dry_run else ''}{len(results)} files extracted successfully with {len(errors)} errors...."
            )

            if len(errors) > 0:
                logging.error(
                    "Errors occurred while extracting source files. Last error:\n",
                    exc_info=errors[-1],
                )

    except Exception as e:
        logging.error("Unexpected error extracting source files")
        raise e
    except SystemExit:
        raise typer.Abort()


@app.command(
    "transform",
    help="Create intermediate files (.transform.yml) of the source files in `source` directory",
)
def run_transform_command(
    directory_filter: cli_utils.DirectoryFilterArgument = None,
    # file_search_pattern: cli_utils.FileFilterArgument = None,
    dry_run: cli_utils.DryRunOption = False,
    limit: cli_utils.LimitOption = None,
    overwrite: cli_utils.OverwriteOption = False,
):
    cli_utils.validate_confirm_active_project()

    try:
        project_source_documents_path = Path(
            _global_config.get_project_base_path(),
            Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
        )

        source_directories = get_filtered_directories(
            directory_filter=directory_filter,
            base_path=project_source_documents_path,
        )

        if not source_directories:
            logging.warning(
                f"No source directories found matching the filter '{directory_filter}'"
            )
            return

        # Module local import (speed up CLI start time)
        from charmina.modules.transform.transform_runner import TransformRunner

        project_config = _global_config.get_project_config()
        runner = TransformRunner(
            **project_config["transform"],
        )

        for source_directory in source_directories:
            typer.echo(
                f"\nTransforming {LogColors.URL}{source_directory}{LogColors.ENDC}"
            )
            tqdm_holder = cli_utils.TqdmHolder(desc="Completed", ncols=80)
            runner.on("start", tqdm_holder.start)
            runner.on("update", tqdm_holder.update)
            runner.on("write", tqdm_holder.write)
            runner.on("close", tqdm_holder.close)

            results, errors = runner.run(
                source_directory=str(source_directory),
                source_root_path=Path(
                    _global_config.get_project_base_path(),
                    Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
                ),
                dry_run=dry_run,
                limit=limit,
                overwrite=overwrite,
            )

            tqdm_holder.close()
            typer.echo(
                f"\n{'[Dry run] ' if dry_run else ''}{len(results)} files transformed successfully with {len(errors)} errors...."
            )

            if len(errors) > 0:
                logging.error(
                    "Errors occurred while transforming source files. Last error:\n",
                    exc_info=errors[-1],
                )

    except Exception as e:
        logging.error("Unexpected error transforming source files")
        raise e
    except SystemExit:
        raise typer.Abort()


@app.command(
    "scribe",
    help="Scribe the final files (.md) from the intermediate (.transform.yml) and metadata (.meta.yml) files in 'output' directory",
)
def run_scribe_command(
    directory_filter: cli_utils.DirectoryFilterArgument = None,
    # file_search_pattern: cli_utils.FileFilterArgument = None,
    dry_run: cli_utils.DryRunOption = False,
    limit: cli_utils.LimitOption = None,
    overwrite: cli_utils.OverwriteOption = False,
):
    cli_utils.validate_confirm_active_project()

    try:
        project_source_documents_path = Path(
            _global_config.get_project_base_path(),
            Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
        )

        source_directories = get_filtered_directories(
            directory_filter=directory_filter,
            base_path=project_source_documents_path,
        )

        if not source_directories:
            logging.warning(
                f"No source directories found matching the filter '{directory_filter}'"
            )
            return

        # Module local import (speed up CLI start time)
        from charmina.modules.scribe.scribe_runner import ScribeRunner

        project_config = _global_config.get_project_config()
        runner = ScribeRunner(
            templates=project_config["templates"],
            **project_config["scribe"],
        )

        for source_directory in source_directories:
            typer.echo(f"\nScribing {LogColors.URL}{source_directory}{LogColors.ENDC}")
            tqdm_holder = cli_utils.TqdmHolder(desc="Completed", ncols=80)
            runner.on("start", tqdm_holder.start)
            runner.on("update", tqdm_holder.update)
            runner.on("write", tqdm_holder.write)
            runner.on("close", tqdm_holder.close)

            results, errors = runner.run(
                source_directory=str(source_directory),
                source_root_path=Path(
                    _global_config.get_project_base_path(),
                    Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME,
                ),
                output_root_path=Path(
                    _global_config.get_project_base_path(),
                    Config._PROJECT_OUTPUT_DOCUMENTS_DIRECTORYNAME,
                ),
                dry_run=dry_run,
                limit=limit,
                overwrite=overwrite,
            )

            tqdm_holder.close()
            typer.echo(
                f"\n{'[Dry run] ' if dry_run else ''}{len(results)} files scribed successfully with {len(errors)} errors...."
            )

            if len(errors) > 0:
                logging.error(
                    "Errors occurred while scribing source files. Last error:\n",
                    exc_info=errors[-1],
                )

    except Exception as e:
        logging.error("Unexpected error scribing source files")
        raise e
    except SystemExit:
        raise typer.Abort()
