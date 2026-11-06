import os
import json
from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """
    Синглтон для работы с JSON-файлами.
    Инкапсулирует пути и методы чтения/записи.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_data_dir'):
            settings = SettingsLoader()
            self._data_dir = settings.get("DATA_DIR", "data")

    def load(self, filename: str, default_factory=list):
        """Загружает данные из JSON-файла."""
        filepath = os.path.join(self._data_dir, filename)

        if not os.path.exists(filepath):
            return default_factory()

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return default_factory()
                return json.loads(content)
        except json.JSONDecodeError:
            return default_factory()

    def save(self, filename: str, data: list | dict) -> None:
        """Атомарно сохраняет данные в JSON-файл."""
        if not os.path.exists(self._data_dir):
            os.makedirs(self._data_dir)

        filepath = os.path.join(self._data_dir, filename)
        temp_filepath = filepath + ".tmp"

        try:
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            os.replace(temp_filepath, filepath)

        except Exception as e:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            raise e