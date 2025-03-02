from typing import Optional
from typing_extensions import Annotated
import typer
import logging
import yaml
from rich.console import Console
from rich.syntax import Syntax
from charmina.config import Config
from charmina.cli import cli_projects, cli_runners, cli_utils


app = typer.Typer(cls=cli_utils.OrderedCommandsTyperGroup, no_args_is_help=True)
# app.registered_commands += cli_....app.registered_commands


# Default command
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        app.show_help(ctx)

    if ctx.command == "test":
        print("Running test command...")


@app.command("env", help="Print the current value of environment variables")
def env_command():

    console = Console()

    syntax = Syntax(
        "\n".join(
            [
                "# Current environment variables",
                "# See more info in https://github.com/raulonlab/charmina/blob/main/.env_example",
                str(Config.instance()),
            ]
        ),
        "ini",
        line_numbers=False,
    )  # , theme="monokai"
    console.print(syntax)


@app.command("config", help="Print the active project configuration (config.yml)")
def config_command(
    section: Annotated[
        Optional[str],
        typer.Argument(help="Print only a specific section of the config"),
    ] = None,
):

    project_config = Config.instance().get_project_config()

    if section:
        if section in project_config:
            project_config = {section: project_config[section]}
        else:
            logging.error(f"Section '{section}' not found in the active project config")
            return

    config_yaml = yaml.safe_dump(
        project_config,
        stream=None,
        default_flow_style=False,
        sort_keys=False,
    )

    syntax = Syntax(
        "\n".join(
            [
                "# Active configuration {section_suffix}".format(
                    section_suffix=f" - {section}" if section else ""
                ),
                "# See more info in https://github.com/raulonlab/charmina/blob/main/charmina/config.yml",
                config_yaml,
            ]
        ),
        "yaml",
        line_numbers=False,
    )  # , theme="monokai"

    console = Console()
    console.print(syntax)


app.add_typer(
    cli_projects.app,
    name="project",
    help="Manage projects: create, activate, deactivate, list and remove",
)

app.add_typer(
    cli_runners.app,
    name="run",
    help="Run pipeline stages: download, extract, transform and scribe",
    epilog="* Require an active project",
)
