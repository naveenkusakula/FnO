from datetime import datetime, timedelta


def get_weekly_expiry():
    today = datetime.today()
    # Find next Thursday (weekly expiry)
    days_until_thursday = (3 - today.weekday()) % 7  # 3 = Thursday
    expiry = today + timedelta(days=days_until_thursday)
    return expiry.strftime("%d-%b-%Y")


class OptionsService:
    def __init__(self, strike_interval=50):
        self.strike_interval = strike_interval

    def round_strike(self, price, direction="ATM"):
        if direction == "ATM":
            return round(price / self.strike_interval) * self.strike_interval
        elif direction == "OTM_CALL":
            return round((price + self.strike_interval) / self.strike_interval) * self.strike_interval
        elif direction == "OTM_PUT":
            return round((price - self.strike_interval) / self.strike_interval) * self.strike_interval
        return None

    def select_option(self, price, position_type):
        expiry = get_weekly_expiry()
        if position_type == "CALL":
            strike = self.round_strike(price, "OTM_CALL")
        elif position_type == "PUT":
            strike = self.round_strike(price, "OTM_PUT")
        else:
            raise ValueError("Invalid position_type")

        option_contract = {
            "strike": strike,
            "type": position_type,
            "expiry": expiry
        }

        print(f"Selected option: {option_contract}")
        return option_contract

    # Placeholder: assumes you have a dict self.option_prices with keys (strike, type, expiry)
    def get_option_prices(self, strike, expiry):
        # Example: self.option_prices = {(strike, 'CALL', expiry): price, (strike, 'PUT', expiry): price}
        call_price = self.option_prices.get((strike, 'CALL', expiry), None)
        put_price = self.option_prices.get((strike, 'PUT', expiry), None)
        return call_price, put_price
