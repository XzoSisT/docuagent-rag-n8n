"""Small, explicit logging setup for the API."""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure a consistent log format for local and container runs."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
