import datetime
from typing import Optional
from valutatrade_hub.parser_service.config import parser_config
from valutatrade_hub.infra.database import DatabaseManager


def _get_utc_now_iso() -> str:
    """Возвращает текущее время в формате UTC."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def save_to_history(
        from_cur: str,
        to_cur: str,
        rate: float,
        source: str,
        meta: Optional[dict] = None  # <-- Добавили Optional
):
    """
    Сохраняет новый замер в exchange_rates.json.
    Формирует уникальный ID: <FROM><TO><TIMESTAMP>.
    """
    timestamp = _get_utc_now_iso()
    record_id = f"{from_cur.upper()}_{to_cur.upper()}_{timestamp}"

    db = DatabaseManager()
    history = db.load(parser_config.HISTORY_FILE_PATH, default_factory=list)

    if not isinstance(history, list):
        history = []

    for record in history:
        if record.get("id") == record_id:
            return

    new_record = {
        "id": record_id,
        "from_currency": from_cur.upper(),
        "to_currency": to_cur.upper(),
        "rate": rate,
        "timestamp": timestamp,
        "source": source,
        "meta": meta or {}  # <-- Безопасная обработка None
    }

    history.append(new_record)
    db.save(parser_config.HISTORY_FILE_PATH, history)


def update_cache(pairs_data: dict):
    """
    Обновляет rates.json. Кэш для Core Service.
    """
    db = DatabaseManager()
    cache = db.load(parser_config.RATES_FILE_PATH, default_factory=dict)

    if not isinstance(cache, dict):
        cache = {}

    if "pairs" not in cache:
        cache["pairs"] = {}

    now_iso = _get_utc_now_iso()

    for pair, info in pairs_data.items():
        new_rate = info["rate"]
        source = info["source"]

        cache["pairs"][pair] = {
            "rate": float(new_rate),
            "updated_at": now_iso,
            "source": source
        }

    cache["last_refresh"] = now_iso
    db.save(parser_config.RATES_FILE_PATH, cache)