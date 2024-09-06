import logging
import typing as t

RESET = "\33[0m"

BOLD = "\33[1m"
GREEN = "\33[32m"
YELLOW = "\33[33m"
RED = "\33[31m"
MAGENTA = "\33[35m"
BLUE = "\33[34m"


FORMAT: t.Final[str] = f"[%(levelname)s]{RESET} %(message)s"
COLORS = {
    logging.DEBUG: BOLD,  # bold default
    logging.INFO: BOLD + GREEN,  # bold green
    logging.WARNING: BOLD + YELLOW,  # bold yellow
    logging.ERROR: BOLD + RED,  # bold red
    logging.CRITICAL: BOLD + MAGENTA,  # bold magenta
}


class Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = COLORS[record.levelno]
        log = color + FORMAT + RESET
        return logging.Formatter(log, style="%").format(record)


def init_logging(debug: bool = False, silent: bool = False) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(Formatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    if debug is True:
        logging.getLogger().setLevel(logging.DEBUG)

    if silent is True:
        logging.disable(logging.ERROR)
