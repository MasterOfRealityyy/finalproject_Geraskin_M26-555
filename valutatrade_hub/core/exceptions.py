class ValutaTradeError(Exception):
    """Базовый класс для всех ошибок проекта."""
    pass


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств для совершения операции."""
    def __init__(self, available: float, required: float, code: str):
        self.message = f"Недостаточно средств: доступно {available:.4f} {code}, требуется {required:.4f} {code}"
        super().__init__(self.message)


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта (нет в реестре или в кэше курсов)."""
    def __init__(self, code: str):
        self.message = f"Неизвестная валюта '{code.upper()}'"
        super().__init__(self.message)


class ApiRequestError(ValutaTradeError):
    """Сбой при обращении к внешнему API."""
    def __init__(self, reason: str = "Неизвестная ошибка"):
        self.message = f"Ошибка при обращении к внешнему API: {reason}"
        super().__init__(self.message)