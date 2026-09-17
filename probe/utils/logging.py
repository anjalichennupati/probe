import logging
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler

console = Console()


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a Logger instance styled with Rich formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger
