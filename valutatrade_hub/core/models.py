import datetime
import hashlib
import hmac
import secrets
from typing import Optional

from valutatrade_hub.core.exceptions import InsufficientFundsError


class User:
    PBKDF2_ITERATIONS = 100000

    def __init__(self, user_id: int, username: str,
                 hashed_password: str, salt: str,
                 registration_date: datetime.datetime):
        self.user_id = user_id
        self.username = username
        self.hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self):
        return self._user_id

    @user_id.setter
    def user_id(self, user_id: int):
        if not isinstance(user_id, int) or user_id < 0:
            raise ValueError("ID должен быть неотрицательным целым числом")
        self._user_id = user_id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username: str):
        cleaned_username = username.strip()
        if not cleaned_username:
            raise ValueError("Имя пользователя не может быть пустым!")
        self._username = cleaned_username

    @property
    def hashed_password(self):
        return self._hashed_password

    @hashed_password.setter
    def hashed_password(self, hashed_password: str):
        if not hashed_password:
            raise ValueError("Хеш пароля не может быть пустым!")
        self._hashed_password = hashed_password

    @property
    def salt(self):
        return self._salt

    @property
    def registration_date(self):
        return self._registration_date

    def get_user_info(self):
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat()
        }

    def change_password(self, new_password: str):
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов!")
        self._salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256',
                                     new_password.encode(),
                                     self._salt.encode(),
                                     self.PBKDF2_ITERATIONS).hex()
        self.hashed_password = hashed

    def verify_password(self, password: str) -> bool:
        test_hash = hashlib.pbkdf2_hmac('sha256',
                                        password.encode(),
                                        self._salt.encode(),
                                        self.PBKDF2_ITERATIONS).hex()
        return hmac.compare_digest(test_hash, self._hashed_password)


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self.balance = balance

    @staticmethod
    def validate_amount(amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом!")
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной!")

    @property
    def currency_code(self):
        return self._currency_code

    @currency_code.setter
    def currency_code(self, currency_code: str):
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты должен быть непустой строкой!")
        self._currency_code = currency_code.upper().strip()

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, balance: float):
        if isinstance(balance, bool) or not isinstance(balance, (float, int)):
            raise ValueError("Баланс должен быть числом!")
        if balance < 0:
            raise ValueError("Баланс не может быть отрицательным!")
        self._balance = balance

    def deposit(self, amount: float):
        self.validate_amount(amount)
        self.balance += amount

    def get_balance_info(self):
        return {
            "currency_code": self.currency_code,
            "balance": float(self._balance)
        }


    def withdraw(self, amount: float):
        self.validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                code=self.currency_code
            )
        self.balance -= amount

class Portfolio:
    def __init__(self, user_id: int, user:Optional[User] = None):
        self._user_id = user_id
        self._user = user
        self._wallets: dict[str, Wallet] = {}

    @property
    def user(self) -> Optional[User]:
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        return self._wallets.copy()

    @property
    def user_id(self) -> int:
        return self._user_id

    def add_currency(self, currency_code: str):
        currency_code = currency_code.upper().strip()
        if currency_code in self._wallets:
            raise ValueError(f"Кошелек с валютой {currency_code}"
                             f" уже находится в портфеле!")
        self._wallets[currency_code] = Wallet(currency_code)

    def get_wallet(self, currency_code: str) -> Wallet:
        currency_code = currency_code.upper().strip()
        if currency_code not in self._wallets:
            raise ValueError(f'Кошелек с валютой {currency_code}'
                             f' отсутствует в портфеле!')
        return self._wallets[currency_code]

    def get_total_value(self, base_currency = 'USD',
                        rates: Optional[dict[str, float]] = None) -> float:
        if rates is None:
            rates = {"USD": 1.0, "EUR": 1.08, "BTC": 60000.0}

        base_currency = base_currency.upper().strip()
        base_rate = rates.get(base_currency)

        if base_rate is None:
            raise ValueError(f"Нет курса для базовой валюты {base_currency}")

        total = 0.0
        for code, wallet in self._wallets.items():
            rate = rates.get(code)
            if rate is None:
                continue
            total += (wallet.balance * rate) / base_rate
        return total















