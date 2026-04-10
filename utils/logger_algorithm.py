"""
This is the logging system for Furina System.
It sets up a rotating file handler that creates a new log file every day and keeps logs depending on the backup count.
It also initializes Sentry for crash telemetry..
"""

import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
import sentry_sdk
import config

# Configures the global logging system with log rotation and initializes Sentry
def initialize_logger() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)

    # Set up a TimedRotatingFileHandler that creates a new log file every day at midnight and keeps 3 days of logs
    rotating_handler = TimedRotatingFileHandler(
        filename="logs/furina.log",
        when="midnight",
        interval=1,
        backupCount=3,
        encoding="utf-8"
    )
    rotating_handler.suffix = "%Y-%m-%d"  # Makes log files look like furina.log.2024-06-01, furina.log.2024-06-02, etc.

    # Configure the Root Logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            rotating_handler,
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Create a specific logger for this setup process
    logger = logging.getLogger("FurinaSystem")

    # Initialize Sentry
    if config.SENTRY_DSN:
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            traces_sample_rate=1.0,
        )
        logger.info("Sentry Telemetry Online!")
    else:
        logger.warning("No Sentry DSN found. Crash telemetry is disabled.")

    return logger