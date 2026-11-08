import datetime
import hashlib
import secrets

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import load_data
from valutatrade_hub.core.сurrencies import get_currency
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


@log_action("REGISTER")
def register_user(username: str, password: str) -> str:
    """Функция для регистрации нового пользователя"""

    db = DatabaseManager()

    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users_data = db.load("users.json")
    for user_dict in users_data:
        if user_dict["username"].lower() == username.lower():
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    if users_data:
        new_id = users_data[-1]["user_id"] + 1
    else:
        new_id = 1

    salt = secrets.token_hex(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256',
                                          password.encode(),
                                          salt.encode(),
                                          100000).hex()

    new_user = User(
        user_id=new_id,
        username=username,
        hashed_password=hashed_password,
        salt=salt,
        registration_date=datetime.datetime.now()
    )

    users_data.append({
        "user_id": new_user.user_id,
        "username": new_user.username,
        "hashed_password": new_user.hashed_password,
        "salt": new_user.salt,
        "registration_date": new_user.registration_date.isoformat()
    })


    portfolios_data = db.load("portfolios.json")
    new_portfolio = Portfolio(user_id=new_user.user_id)

    portfolios_data.append({
        "user_id": new_portfolio.user_id,
        "wallets": {}
    })

    db.save("users.json", users_data)
    db.save("portfolios.json", portfolios_data)


    return (f"Пользователь '{username}' зарегистрирован (id={new_id})."
            f" Войдите: login --username {username} --password {password}")

@log_action("LOGIN")
def login(username: str, password: str) -> User:
    """Функция для входа существующего пользователя"""
    users_data = load_data("users.json")

    user_data: dict | None = None
    for user_dict in users_data:
        if user_dict["username"].lower() == username.lower():
            user_data = user_dict
            break

    if not user_data:
        raise ValueError(f"Пользователь {username} не найден!")

    user_obj = User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        hashed_password=user_data["hashed_password"],
        salt=user_data["salt"],
        registration_date=datetime.datetime.fromisoformat(user_data["registration_date"])
    )

    if not user_obj.verify_password(password):
        raise ValueError("Введен неверный пароль!")

    return user_obj


def validate_currency(currency_code: str) -> str:
    """Проверяет и нормализует код валюты ('usd' -> 'USD')"""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты должен быть непустой строкой!")
    return currency_code.upper().strip()


def get_rate(currency_code: str) -> dict:
    """Возвращает курс валюты к USD с учётом TTL."""
    currency_code = currency_code.upper().strip()
    get_currency(currency_code)

    db = DatabaseManager()
    rates_data = db.load("rates.json", default_factory=dict)

    pairs = rates_data.get("pairs", {})

    if currency_code == "USD":
        return {"rate": 1.0, "updated_at": "now"}

    pair = f"{currency_code}_USD"
    if pair not in pairs:
        raise CurrencyNotFoundError(currency_code)

    rate_info = pairs[pair]
    updated_at_str = rate_info.get("updated_at")

    if updated_at_str:
        try:
            updated_at = datetime.datetime.fromisoformat(updated_at_str)
            now = datetime.datetime.now(datetime.timezone.utc)
            settings = SettingsLoader()
            ttl = settings.get("RATES_TTL_SECONDS", 300)

            if (now - updated_at).total_seconds() > ttl:
                raise ApiRequestError(f"Курс для {currency_code} устарел."
                                      f" Выполните 'update-rates'.")
        except ValueError:
            raise ApiRequestError(f"Неверный формат времени для {currency_code}.")

    return rate_info


def get_cross_rate(from_currency: str, to_currency: str) -> dict:
    """Возвращает курс from_currency к to_currency (кросс-курс)."""
    from_cur = validate_currency(from_currency)
    to_cur = validate_currency(to_currency)

    if from_cur == to_cur:
        return {"rate": 1.0, "updated_at": "now", "inverse_rate": 1.0}

    try:
        from_rate_info = get_rate(from_cur)
        to_rate_info = get_rate(to_cur)
    except ValueError:
        raise ValueError(f"Курс {from_cur}->{to_cur} недоступен. "
                         f"Повторите попытку позже.")

    rate = from_rate_info["rate"] / to_rate_info["rate"]
    inverse_rate = 1 / rate if rate != 0 else 0

    updated_at = to_rate_info["updated_at"]
    if from_rate_info["updated_at"] > updated_at:
        updated_at = from_rate_info["updated_at"]

    return {
        "rate": rate,
        "inverse_rate": inverse_rate,
        "updated_at": updated_at
    }


def get_all_rates() -> dict[str, float]:
    """Возвращает упрощенный словарь курсов: {"USD": 1.0, "EUR": 1.12, и т.д}"""
    db = DatabaseManager()
    rates_data = db.load("rates.json", default_factory=dict)
    rates_dict = {"USD": 1.0}
    pairs = rates_data.get("pairs", {})

    for pair_key, info in pairs.items():
        currency_code = pair_key.split("_")[0]
        rates_dict[currency_code] = info["rate"]

    return rates_dict


def get_portfolio_info(user: User, base_currency: str = "USD") -> dict:
    """Собирает данные о портфеле для вывода в CLI."""
    portfolios_data = load_data("portfolios.json")

    user_portfolio: dict | None = None

    for p in portfolios_data:
        if p["user_id"] == user.user_id:
            user_portfolio = p
            break

    if not user_portfolio:
        raise ValueError("Портфель не найден!")

    portfolio = Portfolio(user_id=user.user_id)
    for code, wallet_data in user_portfolio["wallets"].items():
        portfolio.add_currency(code)
        portfolio.get_wallet(code).balance = wallet_data["balance"]

    base_currency = validate_currency(base_currency)
    rates = get_all_rates()

    total_value = portfolio.get_total_value(base_currency, rates)

    wallets_info = []
    for code, wallet in portfolio.wallets.items():
        rate = rates.get(code)

        if rate is None:
            value_in_base = 0.0
            is_rate_missing = True
        else:
            base_rate: float = rates.get(base_currency, 1.0)
            value_in_base = (wallet.balance * rate) / base_rate
            is_rate_missing = False

        wallets_info.append({
            "code": code,
            "balance": wallet.balance,
            "value": value_in_base,
            "is_rate_missing": is_rate_missing
        })

    return {
        "username": user.username,
        "base_currency": base_currency,
        "wallets": wallets_info,
        "total": total_value
    }


@log_action("BUY", verbose=True)
def buy_currency(user: User, currency_code: str, amount: float) -> dict:
    get_currency(currency_code)

    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    db = DatabaseManager()
    portfolios_data = db.load("portfolios.json")

    user_portfolio: dict | None= next((p for p in portfolios_data
                                       if p["user_id"] == user.user_id), None)
    if not user_portfolio:
        raise ValueError("Портфель не найден.")

    if currency_code not in user_portfolio["wallets"]:
        user_portfolio["wallets"][currency_code] = {"balance": 0.0}

    old_balance = user_portfolio["wallets"][currency_code]["balance"]

    rate_data = get_cross_rate("USD", currency_code)
    rate = rate_data["rate"]

    user_portfolio["wallets"][currency_code]["balance"] += amount
    new_balance = user_portfolio["wallets"][currency_code]["balance"]

    db.save("portfolios.json", portfolios_data)

    total_cost = amount / rate

    return {
        "currency": currency_code.upper(),
        "amount": amount,
        "rate": total_cost / amount if amount > 0 else 0,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "total_cost": total_cost
    }


@log_action("SELL", verbose=True)
def sell_currency(user: User, currency_code: str, amount: float) -> dict:
    get_currency(currency_code)
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    db = DatabaseManager()
    portfolios_data = db.load("portfolios.json")

    user_portfolio: dict | None = next((p for p in portfolios_data
                                        if p["user_id"] == user.user_id), None)
    if not user_portfolio:
        raise ValueError("Портфель не найден.")

    if currency_code not in user_portfolio["wallets"]:
        raise InsufficientFundsError(available=0.0,
                                     required=amount,
                                     code=currency_code)

    old_balance = user_portfolio["wallets"][currency_code]["balance"]
    if old_balance < amount:
        raise InsufficientFundsError(available=old_balance,
                                     required=amount,
                                     code=currency_code)

    rate_data = get_cross_rate("USD", currency_code)
    rate = rate_data["rate"]

    user_portfolio["wallets"][currency_code]["balance"] -= amount
    new_balance = user_portfolio["wallets"][currency_code]["balance"]

    db.save("portfolios.json", portfolios_data)

    total_cost = amount / rate  # Оценочная выручка в USD

    return {
        "currency": currency_code.upper(),
        "amount": amount,
        "rate": total_cost / amount if amount > 0 else 0,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "total_cost": total_cost
    }


def get_cached_rates(currency: str | None = None, top: int | None = None) -> dict:
    """Возвращает курсы из кэша с учетом фильтров."""
    db = DatabaseManager()
    rates_data = db.load("rates.json", default_factory=dict)

    pairs = rates_data.get("pairs", {})
    last_refresh = rates_data.get("last_refresh", "unknown")

    if not pairs:
        raise ValueError("Локальный кеш курсов пуст. "
                         "Выполните 'update-rates', чтобы загрузить данные.")

    if currency:
        currency = currency.upper()
        filtered = {}
        for pair, info in pairs.items():
            if pair.startswith(f"{currency}_") or pair.endswith(f"_{currency}"):
                filtered[pair] = info

        if not filtered:
            raise ValueError(f"Курс для '{currency}' не найден в кеше.")

        return {"last_refresh": last_refresh, "pairs": filtered}

    if top:
        sorted_items = sorted(
            pairs.items(),
            key=lambda item: item[1]["rate"],
            reverse=True
        )

        top_pairs = {k: v for k, v in sorted_items[:top]}

        return {"last_refresh": last_refresh, "pairs": top_pairs}

    sorted_pairs = {k: pairs[k] for k in sorted(pairs.keys())}
    return {"last_refresh": last_refresh, "pairs": sorted_pairs}