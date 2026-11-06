import datetime
import secrets
import hashlib

from valutatrade_hub.core.models import User, Portfolio
from valutatrade_hub.core.utils import load_data, save_data


def register_user(username: str, password: str) -> str:
    """Функция для регистрации нового пользователя"""

    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users_data = load_data("users.json")
    for user_dict in users_data:
        if user_dict["username"].lower() == username.lower():
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    if users_data:
        new_id = users_data[-1]["user_id"] + 1
    else:
        new_id = 1

    salt = secrets.token_hex(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

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


    portfolios_data = load_data("portfolios.json")
    new_portfolio = Portfolio(user_id=new_user.user_id)

    portfolios_data.append({
        "user_id": new_portfolio.user_id,
        "wallets": {}
    })

    save_data("portfolios.json", portfolios_data)
    save_data("users.json", users_data)

    return f"Пользователь '{username}' зарегистрирован (id={new_id}). Войдите: login --username {username} --password {password}"

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
    """
    Возвращает словарь с курсом валюты к USD.
    """
    currency_code = validate_currency(currency_code)
    rates_data = load_data("rates.json", default_factory=dict)

    if currency_code == "USD":
        return {
            "rate": 1.0,
            "updated_at": rates_data.get("last_refresh", "Unknown")
        }

    pair = f"{currency_code}_USD"

    if pair not in rates_data:
        raise ValueError(f"Курс для валюты {currency_code} не найден.")

    return rates_data[pair]


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
        raise ValueError(f"Курс {from_cur}->{to_cur} недоступен. Повторите попытку позже.")

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
    """Возвращает упрощенный словарь курсов: {"USD": 1.0, "EUR": 1.0786, ...}"""
    rates_data = load_data("rates.json", default_factory=dict)
    rates_dict = {"USD": 1.0}

    for pair, info in rates_data.items():
        if pair in ("source", "last_refresh"):
            continue
        currency = pair.split("_")[0]
        rates_dict[currency] = info["rate"]

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
        rate = rates.get(code, 0)
        base_rate = rates.get(base_currency, 1.0)
        value_in_base = (wallet.balance * rate) / base_rate
        wallets_info.append({
            "code": code,
            "balance": wallet.balance,
            "value": value_in_base
        })

    return {
        "username": user.username,
        "base_currency": base_currency,
        "wallets": wallets_info,
        "total": total_value
    }


def buy_currency(user: User, currency_code: str, amount: float) -> dict:
    """Покупает валюту: пополняет кошелек и возвращает данные для отчета."""

    currency_code = validate_currency(currency_code)
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    portfolios_data = load_data("portfolios.json")
    user_portfolio: dict | None  = None
    for p in portfolios_data:
        if p["user_id"] == user.user_id:
            user_portfolio = p
            break

    if not user_portfolio:
        raise ValueError("Портфель не найден.")

    if currency_code not in user_portfolio["wallets"]:
        user_portfolio["wallets"][currency_code] = {"balance": 0.0}

    old_balance = user_portfolio["wallets"][currency_code]["balance"]

    user_portfolio["wallets"][currency_code]["balance"] += amount
    new_balance = user_portfolio["wallets"][currency_code]["balance"]

    save_data("portfolios.json", portfolios_data)

    try:
        rate_info = get_rate(currency_code)
        rate = rate_info["rate"]
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {currency_code}=USD")

    total_cost = amount * rate

    return {
        "currency": currency_code,
        "amount": amount,
        "rate": rate,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "total_cost": total_cost
    }


def sell_currency(user: User, currency_code: str, amount: float) -> dict:
    """Продает валюту: уменьшает баланс кошелька и возвращает данные для отчета."""
    currency_code = validate_currency(currency_code)
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    portfolios_data = load_data("portfolios.json")
    user_portfolio: dict | None = None
    for p in portfolios_data:
        if p["user_id"] == user.user_id:
            user_portfolio = p
            break

    if not user_portfolio:
        raise ValueError("Портфель не найден!")

    if currency_code not in user_portfolio["wallets"]:
        raise ValueError(f"У вас нет кошелька для валюты {currency_code}")

    old_balance = user_portfolio["wallets"][currency_code]["balance"]

    if old_balance < amount:
        raise ValueError(f"Недостаточно средств на счете! Баланс: {old_balance:.4f} {currency_code}")

    user_portfolio["wallets"][currency_code]["balance"] -= amount
    new_balance = user_portfolio["wallets"][currency_code]["balance"]

    save_data("portfolios.json", portfolios_data)

    try:
        rate_info = get_rate(currency_code)
        rate = rate_info["rate"]
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {currency_code}=USD")

    total_cost = amount * rate

    return {
        "currency": currency_code,
        "amount": amount,
        "rate": rate,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "total_cost": total_cost
    }