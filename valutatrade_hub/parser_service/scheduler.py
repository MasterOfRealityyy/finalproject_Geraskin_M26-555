import logging
import time

import valutatrade_hub.parser_service.storage as storage
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger("valutatrade")


def run_scheduler(interval_seconds: int = 300):
    """
    Запускает бесконечный цикл обновления курсов.
    параметр interval_seconds: Интервал между обновлениями в секундах.
    """
    logger.info(f"Планировщик запущен. Интервал обновления: {interval_seconds} секунд.")
    clients = [CoinGeckoClient(), ExchangeRateApiClient()]
    updater = RatesUpdater(clients=clients, storage_module=storage)

    try:
        while True:
            logger.info("Плановое обновление курсов...")
            try:
                count = updater.run_update()
                logger.info(f"Плановое обновление завершено. Обновлено пар: {count}.")
            except Exception as e:
                logger.error(f"Ошибка во время планового обновления: {e}")

            logger.info(f"Ожидание следующего обновления ({interval_seconds} сек.)...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        logger.info("Планировщик остановлен пользователем (Ctrl+C).")


if __name__ == "__main__":
    setup_logging()
    settings = SettingsLoader()
    interval = settings.get("RATES_TTL_SECONDS", 300)

    run_scheduler(interval_seconds=interval)