import logging
import os
from logging.handlers import RotatingFileHandler
from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging():
    settings = SettingsLoader()
    log_level = getattr(logging, settings.get("LOG_LEVEL", "INFO").upper())
    log_format = settings.get("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")

    os.makedirs("logs", exist_ok=True)

    sys_logger = logging.getLogger("valutatrade")
    sys_logger.setLevel(log_level)

    action_logger = logging.getLogger("valutatrade_actions")
    action_logger.setLevel(log_level)

    if not sys_logger.handlers:
        sys_handler = RotatingFileHandler("logs/app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        sys_handler.setFormatter(logging.Formatter(log_format))
        sys_logger.addHandler(sys_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        sys_logger.addHandler(console_handler)

    if not action_logger.handlers:
        action_format = "%(levelname)s %(message)s"
        action_handler = RotatingFileHandler("logs/actions.log", maxBytes=5 * 1024 * 1024, backupCount=3,
                                             encoding="utf-8")
        action_handler.setFormatter(logging.Formatter(action_format))
        action_logger.addHandler(action_handler)

    sys_logger.info("Логирование успешно настроено.")