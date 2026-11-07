import time
import requests
from abc import ABC, abstractmethod
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import parser_config
import logging

logger = logging.getLogger("valutatrade")

class BaseApiClient(ABC):
    """Абстрактный базовый класс для всех API-клиентов."""

    @abstractmethod
    def fetch_rates(self) -> list[dict]:
        """
        Должен возвращать список словарей вида:
        [{"pair": "BTC_USD", "rate": 59337.21, "meta": {...}}, ...]
        """
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент для получения криптовалют с CoinGecko."""

    def fetch_rates(self) -> list[dict]:
        crypto_ids = ",".join(parser_config.CRYPTO_ID_MAP.values())

        params = {
            "ids": crypto_ids,
            "vs_currencies": parser_config.BASE_FIAT_CURRENCY.lower()  # "usd"
        }

        start_time = time.perf_counter()
        try:
            response = requests.get(
                parser_config.COINGECKO_URL,
                params=params,
                timeout=parser_config.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            request_ms = int((time.perf_counter() - start_time) * 1000)

        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка сети при запросе к CoinGecko: {e}")
        except ValueError:
            raise ApiRequestError("CoinGecko вернул некорректный JSON.")

        results = []
        base_cur = parser_config.BASE_FIAT_CURRENCY.upper()

        for ticker, raw_id in parser_config.CRYPTO_ID_MAP.items():
            if raw_id in data and base_cur.lower() in data[raw_id]:
                rate = data[raw_id][base_cur.lower()]

                results.append({
                    "pair": f"{ticker}_{base_cur}",
                    "rate": float(rate),
                    "meta": {
                        "raw_id": raw_id,
                        "request_ms": request_ms,
                        "status_code": response.status_code
                    }
                })

        return results


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для получения фиатных валют с ExchangeRate-API."""

    def fetch_rates(self) -> list[dict]:

        if not parser_config.EXCHANGERATE_API_KEY:
            logger.warning("Ключ ExchangeRate-API не найден. Используются тестовые данные.")
            return [
                {"pair": "EUR_USD", "rate": 0.92, "meta": {"raw_id": "USD", "request_ms": 0, "status_code": 200}},
                {"pair": "GBP_USD", "rate": 0.79, "meta": {"raw_id": "USD", "request_ms": 0, "status_code": 200}},
                {"pair": "RUB_USD", "rate": 90.0, "meta": {"raw_id": "USD", "request_ms": 0, "status_code": 200}},
            ]

        base_cur = parser_config.BASE_FIAT_CURRENCY.upper()
        url = f"{parser_config.EXCHANGERATE_API_URL}/{parser_config.EXCHANGERATE_API_KEY}/latest/{base_cur}"

        start_time = time.perf_counter()
        try:
            response = requests.get(url, timeout=parser_config.REQUEST_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            request_ms = int((time.perf_counter() - start_time) * 1000)

        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка сети при запросе к ExchangeRate-API: {e}")
        except ValueError:
            raise ApiRequestError("ExchangeRate-API вернул некорректный JSON.")

        if data.get("result") == "error":
            error_type = data.get("error-type", "unknown")
            raise ApiRequestError(f"ExchangeRate-API вернул ошибку: {error_type}")

        results = []
        rates_dict = data.get("conversion_rates", {})

        for currency in parser_config.FIAT_CURRENCIES:
            if currency in rates_dict:
                rate = rates_dict[currency]

                results.append({
                    "pair": f"{currency}_{base_cur}",
                    "rate": float(rate),
                    "meta": {
                        "raw_id": base_cur,
                        "request_ms": request_ms,
                        "status_code": response.status_code
                    }
                })

        return results