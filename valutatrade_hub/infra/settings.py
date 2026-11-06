import os
import json

class SettingsLoader:
    """
    Синглтон для загрузки и кеширования конфигурации проекта.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_settings'):
            self._settings = {
                "DATA_DIR": "data",
                "RATES_TTL_SECONDS": 300,  # 5 минут
                "BASE_CURRENCY": "USD",
                "LOG_LEVEL": "INFO",
                "LOG_FORMAT": "%(asctime)s - %(levelname)s - %(message)s"
            }
            self._load_config_file()

    def _load_config_file(self):
        """Пытается загрузить настройки из config.json в корне проекта."""
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    self._settings.update(user_config)
            except Exception as e:
                print(f"Ошибка при чтении config.json: {e}")

    def get(self, key: str, default=None):
        """Возвращает значение настройки по ключу."""
        return self._settings.get(key, default)

    def reload(self):
        """Перезагружает конфигурацию (сбрасывает кеш и читает файл заново)."""
        self._settings = {
            "DATA_DIR": "data",
            "RATES_TTL_SECONDS": 300,
            "BASE_CURRENCY": "USD",
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "%(asctime)s - %(levelname)s - %(message)s"
        }
        self._load_config_file()
        print("Конфигурация успешно перезагружена.")