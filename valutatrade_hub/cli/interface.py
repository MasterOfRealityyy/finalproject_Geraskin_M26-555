import shlex
import sys
from prettytable import PrettyTable
from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError
from valutatrade_hub.core.сurrencies import get_all_currency_codes



def print_help():
    """Выводит список доступных команд"""
    print("\nДоступные команды:")
    print("  register <username> <password> - Зарегистрировать нового пользователя")
    print("  login <username> <password>    - Войти в систему")
    print("  show-portfolio                 - Показать портфель и балансы")
    print("  buy <currency> <amount>        - Купить валюту")
    print("  sell <currency> <amount>       - Продать валюту")
    print("  get-rate <currency>            - Получить текущий курс валюты")
    print("  help                           - Показать это сообщение")
    print("  exit                           - Выйти из программы")
    print()


def run():
    print("Вас приветствует ValutaTrade Hub!")
    print("Введите 'help' для списка команд!")
    current_user = None

    while True:
        try:
            user_input = input("Введите команду: ").strip()
            if not user_input:
                continue

            args = shlex.split(user_input)
            command = args[0].lower()

            match command:
                case "exit":
                    print("Выход из программы")
                    sys.exit(0)


                case "register":
                    try:
                        username_index = args.index("--username") + 1
                        password_index = args.index("--password") + 1
                        username = args[username_index]
                        password = args[password_index]
                    except ValueError:
                        print("Ошибка: неверный формат. Используйте: register --username <name> --password <pass>")
                        continue
                    try:
                        result_message = usecases.register_user(username, password)
                        print(result_message)
                    except ValueError as e:
                        print(f"Ошибка: {e}")


                case "login":
                    try:
                        username_index = args.index("--username") + 1
                        password_index = args.index("--password") + 1
                        username = args[username_index]
                        password = args[password_index]
                    except ValueError:
                        print("Ошибка: используйте 'login --username <name> --password <pass>'")
                        continue
                    try:
                        current_user = usecases.login(username, password)
                        print(f"Вы вошли как '{current_user.username}'")
                    except ValueError as e:
                        print(f"Ошибка: {e}")

                case "show-portfolio":
                    if current_user is None:
                        print("Сначала выполните login")
                        continue

                    base_cur = "USD"
                    if "--base" in args:
                        try:
                            base_index = args.index("--base") + 1
                            base_cur = args[base_index]
                        except IndexError:
                            print("Ошибка: после --base нужно указать валюту.")
                            continue

                    try:
                        data = usecases.get_portfolio_info(current_user, base_cur)

                        if not data["wallets"]:
                            print("У вас пока нет кошельков.")
                            continue

                        print(f"Портфель пользователя '{data['username']}' (база: {data['base_currency']}):")

                        table = PrettyTable()
                        table.border = False
                        table.header = False
                        table.align = "l"
                        table.padding_width = 1

                        for w in data["wallets"]:
                            bal_str = f"- {w['code']}: {w['balance']:.4f}"
                            if w.get("is_rate_missing"):
                                val_str = "-> (курс недоступен)"
                            else:
                                val_str = f"-> {w['value']:.2f} {data['base_currency']}"
                            table.add_row([bal_str, val_str])

                        print(table)
                        print("-" * 30)
                        print(f"ИТОГО: {data['total']:.2f} {data['base_currency']}")

                    except ValueError as e:
                        print(f"Ошибка: {e}")


                case "buy":
                    if current_user is None:
                        print("Сначала выполните login")
                        continue

                    try:
                        curr_idx = args.index("--currency") + 1
                        amt_idx = args.index("--amount") + 1
                        currency = args[curr_idx]
                        amount = float(args[amt_idx])
                    except (ValueError, IndexError):
                        print("Ошибка: используйте 'buy --currency <code> --amount <number>'")
                        continue

                    try:
                        result = usecases.buy_currency(user = current_user, currency_code= currency, amount=amount)

                        print(
                            f"Покупка выполнена: {result['amount']:.4f} {result['currency']} по курсу {result['rate']:.2f} USD/{result['currency']}")
                        print("Изменения в портфеле:")
                        print(
                            f" - {result['currency']}: было {result['old_balance']:.4f} -> стало {result['new_balance']:.4f}")
                        print(f"Оценочная стоимость покупки: {result['total_cost']:.2f} USD")


                    except CurrencyNotFoundError as e:
                        available = ", ".join(get_all_currency_codes())
                        print(f"Ошибка: {e}")
                        print(f"Доступные валюты: {available}")
                    except ApiRequestError as e:
                        print(f"Ошибка: {e}")
                        print("Попробуйте повторить позже или проверьте подключение к сети.")
                    except ValueError as e:
                        print(f"Ошибка: {e}")

                case "sell":
                    if current_user is None:
                        print("Сначала выполните login")
                        continue

                    try:
                        curr_idx = args.index("--currency") + 1
                        amt_idx = args.index("--amount") + 1
                        currency = args[curr_idx]
                        amount = float(args[amt_idx])
                    except (ValueError, IndexError):
                        print("Ошибка: используйте 'sell --currency <code> --amount <number>'")
                        continue

                    try:
                        result = usecases.sell_currency(user = current_user, currency_code= currency, amount = amount)

                        print(
                            f"Продажа выполнена: {result['amount']:.4f} {result['currency']} по курсу {result['rate']:.2f} USD/{result['currency']}")
                        print("Изменения в портфеле:")
                        print(
                            f" - {result['currency']}: было {result['old_balance']:.4f} -> стало {result['new_balance']:.4f}")
                        print(f"Оценочная стоимость продажи: {result['total_cost']:.2f} USD")

                    except InsufficientFundsError as e:
                        print(f"Ошибка: {e}")
                    except CurrencyNotFoundError as e:
                        available = ", ".join(get_all_currency_codes())
                        print(f"Ошибка: {e}")
                        print(f"Доступные валюты: {available}")
                    except ValueError as e:
                        print(f"Ошибка: {e}")

                case "get-rate":
                    try:
                        from_idx = args.index("--from") + 1
                        to_idx = args.index("--to") + 1
                        from_cur = args[from_idx]
                        to_cur = args[to_idx]
                    except (ValueError, IndexError):
                        print("Ошибка: используйте 'get-rate --from <code> --to <code>'")
                        continue

                    try:
                        result = usecases.get_cross_rate(from_cur, to_cur)
                        print(
                            f"Курс {from_cur.upper()}->{to_cur.upper()}: {result['rate']:.8f} (обновлено: {result['updated_at']})")
                        print(f"Обратный курс {to_cur.upper()}->{from_cur.upper()}: {result['inverse_rate']:.2f}")


                    except CurrencyNotFoundError as e:
                        available = ", ".join(get_all_currency_codes())
                        print(f"Ошибка: {e}")
                        print(f"Доступные валюты: {available}")
                    except ApiRequestError as e:
                        print(f"Ошибка: {e}")
                        print("Попробуйте повторить позже или проверьте подключение к сети.")
                    except ValueError as e:
                        print(f"Ошибка: {e}")


                case "help":
                    print_help()


                case _:
                    print(f"Неизвестная команда: {command}")

        except Exception as e:
            print(f"Системная ошибка: {e}")


if __name__ == "__main__":
    run()