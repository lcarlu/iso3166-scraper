import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Console only shows progress/warnings/errors; the full DEBUG trace
# (including per-row parsing detail) always goes to the log file so it's
# available for troubleshooting without drowning interactive output.
CONSOLE_LEVEL = logging.INFO
FILE_LEVEL = logging.DEBUG

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S",
            style="%"
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(CONSOLE_LEVEL)
        console_handler.setFormatter(formatter)

        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, 'application.log'),
            maxBytes=5 * 1024 * 1024,  # 5 Mo
            backupCount=3
        )
        file_handler.setLevel(FILE_LEVEL)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger