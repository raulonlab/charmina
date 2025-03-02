# Config consts
import os
from pathlib import Path
from typing import Any, Dict, Optional, List, Union, ClassVar
from dotenv import load_dotenv
from deepmerge import always_merger
import yaml
from dataclasses import dataclass, fields

_RUNTIME_DOTENV_PATH = ".charmina.env"

load_dotenv(dotenv_path=".env", override=True)  # load default .env file
load_dotenv(
    dotenv_path=_RUNTIME_DOTENV_PATH, override=True
)  # load runtime .env file (save env vars between runs)


@dataclass
class Config(object):
    _PROJECT_STORE_DIRECTORYNAME: ClassVar[str] = (
        "db_files"  # Name of the project store directory
    )
    _PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME: ClassVar[str] = (
        "source"  # Name of the directory containing the source documents used as an input of the transformation process
    )
    _PROJECT_OUTPUT_DOCUMENTS_DIRECTORYNAME: ClassVar[str] = (
        "output"  # Name of the directory where the transformed documents are saved
    )
    _PROJECT_CONFIG_FILENAME: ClassVar[str] = (
        "config.yml"  # Name of the project config file
    )
    _PROJECT_CONFIG_TEMPLATES_FILENAME: ClassVar[str] = (
        "config.templates.yml"  # Name of the project config templates file
    )
    _PROJECT_CONFIG_PROMPTS_FILENAME: ClassVar[str] = (
        "config.prompts.yml"  # Name of the project config prompts file
    )
    _YOUTUBE_SOURCES_FILENAME: ClassVar[str] = (
        "youtube.sources"  # Name of the youtube sources file
    )
    _PODCAST_SOURCES_FILENAME: ClassVar[str] = (
        "podcast.sources"  # Name of the podcast sources file
    )

    _instance: ClassVar = None  # singleton instance with environment values

    ACTIVE_PROJECT: Union[str, None] = (
        None  # (Default: None) Name of the active project
    )
    PROJECTS_DIRECTORY_PATH: str = (
        "_projects"  # (Default: "_projects") Path to projects root directory
    )
    LOG_FILE_LEVEL: Optional[str] = (
        None  # (Default: None) Logging level for the log file. Values: INFO, WARNING, ERROR, CRITICAL, NOTSET. If None, disable logging to file
    )
    LOG_FILE_PATH: str = (
        "logs/charmina.log"  # (Default: "logs/charmina.log") Path to log file
    )
    VERBOSE: int = (
        1  # (Default: 1) Amount of logs written to stdout (0: none, 1: medium, 2: full)
    )
    OPENAI_API_KEY: str = ""  # (Required) OpenAI API key
    OPENAI_ORG_ID: str = ""  # (Required) OpenAI organization ID
    # OCR_ENGINE: Optional[Literal["surya", "ocrmypdf"]] = None  # (Default: None) OCR engine to use for PDFs
    YOUTUBE_DOWNLOAD_TYPE: str = (
        "audio"  # (Default: "caption") Type of content to download: caption, audio
    )
    YOUTUBE_GROUP_BY_AUTHOR: bool = (
        True  # (Default: True) Group downloaded videos by channel
    )
    YOUTUBE_SLEEP_SECONDS_BETWEEN_DOWNLOADS: int = (
        3  # (Default: 3) Number of seconds to sleep between downloads
    )
    YOUTUBE_ADD_DATE_PREFIX: bool = (
        True  # (Default: True) Prefix all episodes with an ISO8602 formatted date of when they were published. Useful to ensure chronological ordering
    )
    YOUTUBE_SLUGIFY_PATHS: bool = (
        True  # (Default: True) Clean all folders and filename of potentially weird characters that might cause trouble with one or another target filesystem
    )
    YOUTUBE_MAXIMUM_EPISODE_COUNT: int = (
        30  # (Default: 30) Only download the given number of episodes per youtube channel. Useful if you don't really need the entire backlog. Set 0 to disable limit
    )
    PODCAST_UPDATE_ARCHIVE: bool = (
        True  # (Default: True) Force the archiver to only update the feeds with newly added episodes. As soon as the first old episode found in the download directory, further downloading is interrupted
    )
    PODCAST_ADD_DATE_PREFIX: bool = (
        True  # (Default: True) Prefix all episodes with an ISO8602 formatted date of when they were published. Useful to ensure chronological ordering
    )
    PODCAST_SLUGIFY_PATHS: bool = (
        True  # (Default: True) Clean all folders and filename of potentially weird characters that might cause trouble with one or another target filesystem
    )
    PODCAST_GROUP_BY_AUTHOR: bool = (
        True  # (Default: True) Create a subdirectory for each feed (named with their titles) and put the episodes in there
    )
    PODCAST_MAXIMUM_EPISODE_COUNT: int = (
        30  # (Default: 30) Only download the given number of episodes per podcast feed. Useful if you don't really need the entire backlog. Set 0 to disable limit
    )
    PODCAST_SHOW_PROGRESS_BAR: bool = (
        True  # (Default: True) Show a progress bar while downloading
    )
    WHISPER_TRANSCRIPTION_MODEL_NAME: str = (
        "base"  # (Default: "base") Name of the model to use for transcribing audios: tiny, base, small, medium, large
    )
    WHISPER_PACKAGE_NAME: str = (
        "faster-whisper"  # (Default: "faster-whisper") Name of the package to use for transcribing audios: faster-whisper, whisper-mps, whisper
    )
    TRANSCRIPT_ADD_SUMMARY: bool = (
        False  # (Default: False) Include a summary of the transcription in the output file
    )

    def __init__(self, config: dict = None):
        # ref: https://alexandra-zaharia.github.io/posts/python-configuration-and-dataclasses/
        environment_config = Config.instance()

        # initialise with environment values
        for field in fields(environment_config):
            setattr(self, field.name, getattr(environment_config, field.name))

        # initialise with config received
        for config_key, config_value in config.items() if config else []:
            if hasattr(self, config_key):
                setattr(self, config_key, config_value)

    def __str__(self):
        response = ""
        for field in fields(self):
            if field.name.startswith("_"):
                continue
            response += f"{field.name}={getattr(self, field.name)}\n"
        return response

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)

            # Try to load config from environment variables
            for field in fields(cls):
                setattr(
                    cls._instance,
                    field.name,
                    os.environ.get(field.name, getattr(cls._instance, field.name)),
                )

            # fix types
            cls._instance.VERBOSE = int(cls._instance.VERBOSE)
            cls._instance.YOUTUBE_GROUP_BY_AUTHOR = bool(
                cls._instance.YOUTUBE_GROUP_BY_AUTHOR
            )
            cls._instance.YOUTUBE_SLEEP_SECONDS_BETWEEN_DOWNLOADS = int(
                cls._instance.YOUTUBE_SLEEP_SECONDS_BETWEEN_DOWNLOADS
            )
            cls._instance.YOUTUBE_ADD_DATE_PREFIX = bool(
                cls._instance.YOUTUBE_ADD_DATE_PREFIX
            )
            cls._instance.YOUTUBE_SLUGIFY_PATHS = bool(
                cls._instance.YOUTUBE_SLUGIFY_PATHS
            )
            cls._instance.YOUTUBE_MAXIMUM_EPISODE_COUNT = int(
                cls._instance.YOUTUBE_MAXIMUM_EPISODE_COUNT
            )
            cls._instance.PODCAST_ADD_DATE_PREFIX = bool(
                cls._instance.PODCAST_ADD_DATE_PREFIX
            )
            cls._instance.PODCAST_MAXIMUM_EPISODE_COUNT = int(
                cls._instance.PODCAST_MAXIMUM_EPISODE_COUNT
            )
            cls._instance.PODCAST_SHOW_PROGRESS_BAR = bool(
                cls._instance.PODCAST_SHOW_PROGRESS_BAR
            )
            cls._instance.PODCAST_UPDATE_ARCHIVE = bool(
                cls._instance.PODCAST_UPDATE_ARCHIVE
            )
            cls._instance.PODCAST_SLUGIFY_PATHS = bool(
                cls._instance.PODCAST_SLUGIFY_PATHS
            )
            cls._instance.PODCAST_GROUP_BY_AUTHOR = bool(
                cls._instance.PODCAST_GROUP_BY_AUTHOR
            )
            cls._instance.TRANSCRIPT_ADD_SUMMARY = bool(
                cls._instance.TRANSCRIPT_ADD_SUMMARY
            )

        return cls._instance

    def bootstrap(self):
        config = Config.instance()
        projects_path = Path(config.PROJECTS_DIRECTORY_PATH)
        if not projects_path.exists():
            projects_path.mkdir(parents=True, exist_ok=True)

    def get_project_config(
        self, project_name: Optional[str] = None, ignore_project: Optional[bool] = False
    ):
        config = Config.instance()

        project_name = project_name or config.get_active_project() or None
        if not project_name and not ignore_project:
            raise ValueError("No project name provided")

        default_base_path = Path(__file__).parent
        default_config = self.read_project_config(default_base_path)

        if project_name:
            active_project_base_path = config.get_project_base_path(
                project_name=project_name
            )
            active_project_config = self.read_project_config(active_project_base_path)

            merged_project_config = self.merge_config(
                default_config, active_project_config
            )
            merged_project_config["_project_base_path"] = str(active_project_base_path)
        else:
            merged_project_config = default_config
            merged_project_config["_project_base_path"] = str(default_base_path)

        return dict(merged_project_config)

    def get_project_base_path(
        self, project_name: Optional[str] = None
    ) -> Union[str, Path]:
        config = Config.instance()
        project_name = project_name or config.get_active_project() or None
        if not project_name:
            raise ValueError("No project name provided")

        return Path(config.PROJECTS_DIRECTORY_PATH, project_name)

    def get_project_youtube_sources(
        self, project_name: Optional[str] = None
    ) -> List[str]:
        config = Config.instance()
        project_name = project_name or config.get_active_project() or None
        if not project_name:
            raise ValueError("No project name provided")

        project_youtube_sources_path = Path(
            config.PROJECTS_DIRECTORY_PATH, project_name, self._YOUTUBE_SOURCES_FILENAME
        )

        youtube_playlists: List[str] = []
        if os.path.exists(project_youtube_sources_path):
            with open(project_youtube_sources_path) as file_handler:
                for line in file_handler:
                    line = self.strip_source_url(line)
                    if not line or line in youtube_playlists:
                        continue

                    youtube_playlists.append(line)
        return youtube_playlists

    def get_project_podcast_sources(
        self, project_name: Optional[str] = None
    ) -> List[str]:
        config = Config.instance()
        project_name = project_name or config.get_active_project() or None
        if not project_name:
            raise ValueError("No project name provided")

        project_podcast_sources_path = Path(
            config.PROJECTS_DIRECTORY_PATH, project_name, self._PODCAST_SOURCES_FILENAME
        )

        podcast_feeds: List[str] = []
        if os.path.exists(project_podcast_sources_path):
            with open(project_podcast_sources_path) as file_handler:
                for line in file_handler:
                    line = self.strip_source_url(line)
                    if not line or line in podcast_feeds:
                        continue

                    podcast_feeds.append(line)
        return podcast_feeds

    def activate_project(self, project_name: str | None = None):
        # validate project path exists
        if (
            project_name
            and not self.get_project_base_path(project_name=project_name).exists()
        ):
            raise ValueError(
                f"Project '{project_name}' does not exist. Create it first. See charmina project --help."
            )

        # save active project
        os.environ["ACTIVE_PROJECT"] = project_name
        self.ACTIVE_PROJECT = project_name

        # write to disk runtime .env file
        self.dump_runtime_dotenv()

    def get_active_project(self) -> str | None:
        return self.ACTIVE_PROJECT

    def dump_runtime_dotenv(self):
        with open(_RUNTIME_DOTENV_PATH, "w") as file_handler:
            file_handler.write(
                "%s=%s\n" % ("ACTIVE_PROJECT", self.ACTIVE_PROJECT or "")
            )

    @classmethod
    def read_project_config(cls, directory_path: Union[Path, str]) -> Dict[str, Any]:
        directory_path = Path(directory_path)

        project_config = {}

        if directory_path.is_dir():
            # Load main config file
            config_file_path = directory_path / cls._PROJECT_CONFIG_FILENAME
            try:
                with open(config_file_path) as config_file_handler:
                    project_config = yaml.safe_load(config_file_handler)
                    if not project_config:
                        project_config = {}
            except FileNotFoundError:
                project_config = {}

            # Load templates config file
            config_templates_file_path = (
                directory_path / cls._PROJECT_CONFIG_TEMPLATES_FILENAME
            )
            try:
                with open(config_templates_file_path) as config_templates_file_handler:
                    project_config_templates = yaml.safe_load(
                        config_templates_file_handler
                    )
                    if not project_config_templates:
                        project_config_templates = {}
                    project_config["templates"] = project_config_templates
            except FileNotFoundError:
                project_config["templates"] = {}

            # Load prompts config file
            config_prompts_file_path = (
                directory_path / cls._PROJECT_CONFIG_PROMPTS_FILENAME
            )
            try:
                with open(config_prompts_file_path) as config_prompts_file_handler:
                    project_config_prompts = yaml.safe_load(config_prompts_file_handler)
                    if not project_config_prompts:
                        project_config_prompts = {}
                    project_config["prompts"] = project_config_prompts
            except FileNotFoundError:
                project_config["prompts"] = {}

        elif directory_path.is_file():
            try:
                with open(directory_path) as config_file_handler:
                    project_config = yaml.safe_load(config_file_handler)
            except FileNotFoundError:
                pass
        else:
            raise ValueError(f"Invalid project config path: {directory_path}")

        return project_config

    @classmethod
    def merge_config(cls, a: Dict[Any, Any], b: Dict[Any, Any]) -> Dict[Any, Any]:
        c = {}
        always_merger.merge(c, a)
        always_merger.merge(c, b)
        return c

    @classmethod
    def strip_source_url(cls, line: str) -> Union[str, None]:
        line = line.strip()
        if line.startswith("#"):  # Comment as the first character
            return None

        line = line.split(" #")[0]  # Comment after the source url
        line = line.strip()
        if line != "":
            return line

        return None
