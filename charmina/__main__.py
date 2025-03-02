import logging
from charmina.libs.logging_setup import setup as setup_logging
from charmina.config import Config
from charmina.cli.cli import app as charmina_app


def init():
    config = Config.instance()

    # Initialise config (Create projects directory, etc)
    config.bootstrap()

    # Setup logging
    _log_terminal_level = logging.DEBUG
    if config.VERBOSE == 0:
        _log_terminal_level = logging.WARNING
    elif config.VERBOSE == 1:
        _log_terminal_level = logging.INFO
    setup_logging(
        log_terminal_level=_log_terminal_level,
        log_file_level=config.LOG_FILE_LEVEL,
        log_file_path=config.LOG_FILE_PATH,
    )

    # Setup development tools
    try:
        pass
    except ImportError:
        pass


def run_cli():
    charmina_app()


def main():
    init()
    run_cli()


if __name__ == "__main__":
    main()
