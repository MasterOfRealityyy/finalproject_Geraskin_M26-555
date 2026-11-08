import logging

from valutatrade_hub.core.exceptions import ApiRequestError

logger = logging.getLogger("valutatrade")

class RatesUpdater:
    """Точка входа для логики парсинга."""

    def __init__(self, clients: list, storage_module):
        """
        параметр clients: Список экземпляров API-клиентов.
        параметр storage_module: Модуль или объект storage.py.
        """
        self.clients = clients
        self.storage = storage_module

    def run_update(self, source_filter: str | None = None) -> int:
        """Координирует процесс обновления курсов."""
        logger.info("Запуск обновления курсов валют...")
        all_rates_for_cache = {}

        for client in self.clients:
            client_name = client.__class__.__name__

            if source_filter:
                source_filter = source_filter.lower()
                if "coingecko" in source_filter and "CoinGecko" not in client_name:
                    logger.info(f"Пропуск {client_name} (фильтр: {source_filter})")
                    continue
                if ("exchangerate" in source_filter
                        and "ExchangeRate" not in client_name):
                    logger.info(f"Пропуск {client_name} (фильтр: {source_filter})")
                    continue

            logger.info(f"Запрос к {client_name}...")

            try:
                fetched_data = client.fetch_rates()
                logger.info(f"{client_name}: успешно получено {len(fetched_data)} пар.")

                for item in fetched_data:
                    pair = item["pair"]
                    rate = item["rate"]
                    meta = item["meta"]
                    source = "CoinGecko" if (
                            "CoinGecko" in client_name) else "ExchangeRate-API"

                    from_cur, to_cur = pair.split("_")
                    self.storage.save_to_history(
                        from_cur=from_cur,
                        to_cur=to_cur,
                        rate=rate,
                        source=source,
                        meta=meta
                    )

                    cache_rate = rate
                    if source == "ExchangeRate-API" and rate > 0:
                        cache_rate = 1.0 / rate

                    all_rates_for_cache[pair] = {
                        "rate": cache_rate,
                        "source": source
                    }

            except ApiRequestError as e:
                logger.error(f"Ошибка API у {client_name}: {e}")
            except Exception as e:
                logger.error(f"Непредвиденная ошибка у {client_name}: {e}")

        if all_rates_for_cache:
            self.storage.update_cache(all_rates_for_cache)
            logger.info(f"Кэш успешно обновлен."
                        f" Обработано пар: {len(all_rates_for_cache)}.")
        else:
            logger.warning("Не удалось получить данные ни от одного клиента."
                           " Кэш не обновлен.")

        logger.info("Обновление курсов завершено.")
        return len(all_rates_for_cache)