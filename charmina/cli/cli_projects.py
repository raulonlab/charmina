import os
import re
import shutil
from pathlib import Path
import logging
import typer
from charmina.config import Config


YOUTUBE_SOURCES_INITIAL_CONTENT = """
# One url per line. Lines starting with `#` are ignored.
# video urls
# https://www.youtube.com/watch?v=...

# playlist urls
# https://www.youtube.com/playlist?list=...

# channel urls
# https://www.youtube.com/@...
"""

PODCAST_SOURCES_INITIAL_CONTENT = """
# One url per line. Lines starting with `#` are ignored.
# podcast feed urls
# https://feeds.buzzsprout.com/...
# https://feeds.simplecast.com/...
"""

PROJECT_CONFIG_INITIAL_CONTENT = """
# Override default project config
# See default config file in https://github.com/raulonlab/charmina/blob/main/charmina/charmina.config.yml,

"""

PROJECT_CONFIG_PROMPTS_INITIAL_CONTENT = """
# Change the prompts used in the project.
# See default prompts in https://github.com/raulonlab/charmina/blob/main/charmina/charmina.prompts.yml,

"""

PROJECT_CONFIG_TEMPLATES_INITIAL_CONTENT = """
# Change the templates used in the project to render the output files.
# See default templates in https://github.com/raulonlab/charmina/blob/main/charmina/charmina.templates.yml,

"""

_global_config = Config.instance()
app = typer.Typer()


@app.command(
    "create",
    help="Create and initialize a new project with the given name",
)
def create_project(project_name: str):
    if not validate_project_name(project_name):
        logging.error(
            f"Invalid project name '{project_name}'. Project name must start with alphanumeric and underscore characters"
        )
        return

    logging.debug(f"Initializing project '{project_name}'")
    project_path = Path(_global_config.PROJECTS_DIRECTORY_PATH, project_name)
    if project_path.exists():
        confirmation_response = typer.confirm(
            f"Project directory '{project_name}' already exists. Do you want to continue creating the initial project files in it?",
            default=False,
            abort=False,
        )
        if not confirmation_response:
            raise typer.Abort()

    # project directory
    project_path.mkdir(parents=True, exist_ok=True)

    # project subdirectories
    Path(project_path, Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME).mkdir(
        parents=True, exist_ok=True
    )
    Path(project_path, Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME, "youtube").mkdir(
        parents=True, exist_ok=True
    )
    Path(
        project_path, Config._PROJECT_SOURCE_DOCUMENTS_DIRECTORYNAME, "podcasts"
    ).mkdir(parents=True, exist_ok=True)
    Path(project_path, Config._PROJECT_OUTPUT_DOCUMENTS_DIRECTORYNAME).mkdir(
        parents=True, exist_ok=True
    )

    # project sources files. Skip if they already exist
    youtube_sources_path = Path(project_path, Config._YOUTUBE_SOURCES_FILENAME)
    podcast_sources_path = Path(project_path, Config._PODCAST_SOURCES_FILENAME)

    if not youtube_sources_path.exists():
        with open(youtube_sources_path, "w", encoding="utf-8") as file:
            file.write(YOUTUBE_SOURCES_INITIAL_CONTENT)
    else:
        logging.warning(f"Skipping '{youtube_sources_path}' because it already exists")
    if not podcast_sources_path.exists():
        with open(podcast_sources_path, "w", encoding="utf-8") as file:
            file.write(PODCAST_SOURCES_INITIAL_CONTENT)
    else:
        logging.warning(f"Skipping '{podcast_sources_path}' because it already exists")

    # project config files. Skip if they already exist
    config_path = Path(project_path, Config._PROJECT_CONFIG_FILENAME)
    prompts_path = Path(project_path, Config._PROJECT_CONFIG_PROMPTS_FILENAME)
    templates_path = Path(project_path, Config._PROJECT_CONFIG_TEMPLATES_FILENAME)

    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as file:
            file.write(PROJECT_CONFIG_INITIAL_CONTENT)
    else:
        logging.warning(f"Skipping '{config_path}' because it already exists")
    if not prompts_path.exists():
        with open(prompts_path, "w", encoding="utf-8") as file:
            file.write(PROJECT_CONFIG_PROMPTS_INITIAL_CONTENT)
    else:
        logging.warning(f"Skipping '{prompts_path}' because it already exists")
    if not templates_path.exists():
        with open(templates_path, "w", encoding="utf-8") as file:
            file.write(PROJECT_CONFIG_TEMPLATES_INITIAL_CONTENT)
    else:
        logging.warning(f"Skipping '{templates_path}' because it already exists")

    logging.info(f"Project '{project_name}' created")

    # Activate project if no active project
    if not _global_config.get_active_project():
        activate_project(project_name)


@app.command("remove", help="Remove an existing project")
def remove_project(project_name: str):
    logging.debug(f"Deleting project '{project_name}'")
    project_path = Path(_global_config.PROJECTS_DIRECTORY_PATH, project_name)
    if not project_path or not project_path.exists():
        logging.error(f"Project '{project_name}' does not exist")
        return

    # Prompt for confirmation
    confirmation_response = typer.confirm(
        f"Are you sure you want to remove the project files in '{project_path}'?",
        default=False,
        abort=False,
    )
    if not confirmation_response:
        raise typer.Abort()

    shutil.rmtree(project_path)
    logging.info(f"Project '{project_name}' deleted")

    if _global_config.get_active_project() == project_name:
        _global_config.activate_project("")  # deactivate project
        logging.info("Project deactivated")


@app.command("rename", help="Rename an existing project")
def rename_project(project_name: str, new_project_name: str):
    if not validate_project_name(new_project_name):
        logging.error(
            f"Invalid project name '{new_project_name}'. Project name must start with alphanumeric and underscore characters"
        )
        return

    logging.debug(f"Renaming project '{project_name}' to '{new_project_name}'")
    project_path = Path(_global_config.PROJECTS_DIRECTORY_PATH, project_name)
    if not project_path.exists():
        logging.error(f"Project '{project_name}' does not exist")
        return
    new_project_path = Path(_global_config.PROJECTS_DIRECTORY_PATH, new_project_name)
    if new_project_path.exists():
        logging.error(f"Project '{new_project_name}' already exists")
        return
    project_path.rename(new_project_path)

    # Update active project name if necessary
    if _global_config.get_active_project() == project_name:
        _global_config.activate_project(new_project_name)

    logging.info(f"Project '{project_name}' renamed to '{new_project_name}'")


@app.command(
    "activate",
    help="Activate a project. All subsequent commands (run, etc) will use the project's configuration and source files.",
)
def activate_project(project_name: str):
    logging.debug(f"Activating project '{project_name}'")
    project_path = Path(_global_config.PROJECTS_DIRECTORY_PATH, project_name)
    if not project_path.exists():
        logging.error(f"Project '{project_name}' does not exist")
        return

    _global_config.activate_project(project_name)
    logging.info(f"Project '{project_name}' activated")


@app.command("list", help="List all available projects")
def list_projects():
    logging.debug("Listing projects")
    if not os.path.exists(_global_config.PROJECTS_DIRECTORY_PATH):
        logging.info("No directory found for projects")
        return

    projects = os.listdir(_global_config.PROJECTS_DIRECTORY_PATH)
    if not projects:
        logging.info("No projects found")
        return

    for project in projects:
        if not validate_project_name(project):
            continue

        (
            print(f"[ ] {project}")
            if project != _global_config.get_active_project()
            else print(f"[x] {project}")
        )


def validate_project_name(project_name: str):
    return bool(re.match(r"\w", project_name))
