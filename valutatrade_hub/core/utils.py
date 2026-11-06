import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_data(filename: str, default_factory= list):
    """
    Загружает данные из JSON-файла.
    Если файла нет или он пуст, возвращает значение по умолчанию.
    По умолчанию возвращает пустой список (для users.json и portfolios.json).
    Для rates.json передавайте default_factory=dict.
    """
    filepath = os.path.join(DATA_DIR, filename)

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


def save_data(filename: str, data: list | dict) -> None:
    """Безопасно сохраняет данные в JSON-файл"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    filepath = os.path.join(DATA_DIR, filename)
    temp_filepath = filepath + ".tmp"

    try:
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(temp_filepath, filepath)

    except Exception as e:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        raise e