from enum import Enum


class LogColors:
    BOLD = "\033[1m"
    DISABLED = "\033[2m"
    UNDERLINE = "\033[4m"
    PROJECT = "\033[95m"
    BOLDPROJECT = "\033[1m\033[95m"
    HIGHLIGHT = "\033[94m"
    BOLDHIGHLIGHT = "\033[1m\033[94m"
    URL = "\033[4m\033[96m"  # underline cyan
    ENDC = "\033[0m"

    # Message / Log colors
    OK = "\033[92m"  # green
    INFO = "\033[94m"  # blue
    DEBUG = "\033[2m"  # grey
    WARNING = "\033[93m"  # yellow
    ERROR = "\033[91m"  # red
    FATAL = "\033[1m\033[91m"  # bold re

    # Other colors
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"


class Emojis:
    PROJECT = "🧠"
    SOURCE = "📚"
    CHAT = "💬"
    OK = "✔"
    FAIL = "✘"


class DownloadSourceEnum(str, Enum):
    youtube = "youtube"
    podcasts = "podcasts"
