import logging
import functools

logger = logging.getLogger("valutatrade_actions")


def log_action(action: str, verbose: bool = False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            username = "unknown"
            if args and hasattr(args[0], "username"):
                username = args[0].username
            elif "user" in kwargs and hasattr(kwargs["user"], "username"):
                username = kwargs["user"].username
            elif args and isinstance(args[0], str):
                username = args[0]
            elif "username" in kwargs:
                username = kwargs["username"]

            log_data = {
                "action": action,
                "username": f"'{username}'",
            }

            currency = kwargs.get("currency_code") or kwargs.get("currency")
            amount = kwargs.get("amount")

            if currency is None:
                for arg in args:
                    if isinstance(arg, str) and arg.upper() in ["USD", "EUR", "BTC", "ETH", "RUB"]:
                        currency = arg
                        break
            if amount is None:
                for arg in args:
                    if isinstance(arg, (int, float)) and not isinstance(arg, bool):
                        amount = arg
                        break

            if currency:
                log_data["currency"] = f"'{str(currency).upper()}'"
            if amount is not None:
                log_data["amount"] = f"{float(amount):.4f}"

            try:
                result = func(*args, **kwargs)

                if isinstance(result, dict):
                    if "rate" in result:
                        log_data["rate"] = f"{result['rate']:.2f}"
                        log_data["base"] = "'USD'"
                    if verbose and "old_balance" in result and "new_balance" in result:
                        log_data["wallet_state"] = f"{result['old_balance']:.4f}->{result['new_balance']:.4f}"

                log_data["result"] = "OK"
                log_msg = f"{action} " + " ".join(f"{k}={v}" for k, v in log_data.items())
                logger.info(log_msg)

                return result

            except Exception as e:
                log_data["result"] = "ERROR"
                log_data["error_type"] = type(e).__name__
                log_data["error_message"] = f"'{str(e)}'"
                log_msg = f"{action} " + " ".join(f"{k}={v}" for k, v in log_data.items())
                logger.error(log_msg)

                raise e

        return wrapper
    return decorator