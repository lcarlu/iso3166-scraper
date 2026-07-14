import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)  # Niveau par défaut : DEBUG

        formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S",
            style="%"
        )

        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Handler pour le fichier avec rotation
        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, 'application.log'),
            maxBytes=5 * 1024 * 1024,  # 5 Mo
            backupCount=3              # Jusqu'à 3 fichiers de sauvegarde
        )
        file_handler.setFormatter(formatter)

        # Ajout des handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger