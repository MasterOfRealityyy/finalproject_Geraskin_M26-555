from abc import ABC, abstractmethod
from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    def __init__(self, name: str, code: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым.")

        code_clean = code.strip().upper()
        if not (2 <= len(code_clean) <= 5):
            raise ValueError("Код валюты должен содержать от 2 до 5 символов.")

        self.name = name
        self.code = code_clean

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов."""
        pass


class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        mcap_str = f"{self.market_cap:.2e}".replace("e+", "e")
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"


_CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.04e11),
}


def get_currency(code: str) -> Currency:
    code_clean = code.strip().upper()
    if code_clean not in _CURRENCIES:
        raise CurrencyNotFoundError(code_clean)
    return _CURRENCIES[code_clean]

def get_all_currency_codes() -> list[str]:
    """Возвращает список всех поддерживаемых кодов валют."""
    return list(_CURRENCIES.keys())