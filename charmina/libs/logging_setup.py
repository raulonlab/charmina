#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Duallog: https://github.com/acschaefer/duallog/blob/master/duallog/duallog.py

This module contains a function "setup()" that sets up dual logging.
All subsequent log messages are sent both to the console and to a logfile.
Log messages are generated via the "logging" package.

If run, this module illustrates the usage of the duallog package.
"""

import logging.handlers
from typing import Union

# Begin disable package logs
import log

log.silence("datafiles", allow_warning=True)
log.reset()
# End disable package logs

# Define the default logging message formats.
file_msg_format = "%(asctime)s %(levelname)-8s: %(message)s"
console_msg_format = "%(message)s"

# Define the log rotation criteria.
max_bytes = 1024**2
backup_count = 100


def setup(
    log_terminal_level: Union[str, int] = logging.DEBUG,
    log_file_level: Union[str, int, None] = None,
    log_file_path: str = "charmina.log",
):
    """Set up dual logging to console and to logfile.

    When this function is called, it first creates the given logging output directory.
    It then creates a logfile and passes all log messages to come to it.
    The name of the logfile encodes the date and time when it was created, for example "20181115-153559.log".
    All messages with a certain minimum log level are also forwarded to the console.

    Args:
        log_file_path: path of the file where logs are written. Both a
            relative or an absolute path may be specified. If a relative path is
            specified, it is interpreted relative to the working directory.
        log_file_level: defines the minimum level of the messages written to the log file.
        log_terminal_level: defines the minimum level of the messages shown in the terminal.
    """

    # Convert log level strings to logging constants.
    if isinstance(log_terminal_level, str):
        log_terminal_level = getattr(logging, log_terminal_level.upper())
        if not log_terminal_level:
            raise ValueError("Invalid log level: " + log_terminal_level)
    if isinstance(log_file_level, str):
        log_file_level = getattr(logging, log_file_level.upper())

    # Create the root logger.
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if log_file_level is not None and log_file_level != logging.NOTSET:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file_path,
            when="midnight",
            interval=1,
            backupCount=10,
            utc=True,
        )
        file_handler.setLevel(log_file_level)
        file_formatter = logging.Formatter(file_msg_format)
        file_handler.setFormatter(file_formatter)
        file_handler.suffix = "%Y%m%d"
        logger.addHandler(file_handler)

    # Set up logging to the console.
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_terminal_level)
    stream_formatter = logging.Formatter(console_msg_format)
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)


if __name__ == "__main__":
    """Illustrate the usage of the duallog package."""

    # Set up dual logging.
    setup("logtest")

    # Generate some log messages.
    logging.debug("Debug messages are only sent to the logfile.")
    logging.info("Info messages are not shown on the console, too.")
    logging.warning("Warnings appear both on the console and in the logfile.")
    logging.error("Errors get the same treatment.")
    logging.critical("And critical messages, of course.")
