import re
from datetime import datetime, timedelta
from typing import Dict, Tuple


def get_weekly_expiry():
    today = datetime.today()
    # Find next Thursday (weekly expiry)
    days_until_thursday = (3 - today.weekday()) % 7  # 3 = Thursday
    expiry = today + timedelta(days=days_until_thursday)
    return expiry.strftime("%d-%b-%Y")


class OptionsService:
    def __init__(self, strike_interval=50, api_service=None):
        self.strike_interval = strike_interval
        # api_service should be an instance of PositionsService (from get_api_service.py)
        self.api_service = api_service
        # optional local cache / fallback
        self.option_prices: Dict[Tuple[int, str, str], float] = {}

    def round_strike(self, price, direction="ATM"):
        if direction == "ATM":
            return round(price / self.strike_interval) * self.strike_interval
        elif direction == "OTM_CALL":
            return (
                round((price + self.strike_interval) / self.strike_interval)
                * self.strike_interval
            )
        elif direction == "OTM_PUT":
            return (
                round((price - self.strike_interval) / self.strike_interval)
                * self.strike_interval
            )
        return None

    def get_symbol(self, strike, expiry, option_type):
        # build tsym like NIFTY28OCT25C26000
        # Normalize expiry to DDMMMYY uppercase
        try:
            dt = datetime.strptime(expiry, "%d-%b-%Y")
        except Exception:
            try:
                dt = datetime.strptime(expiry, "%d-%b-%y")
            except Exception:
                dt = datetime.now()  # Fallback? Should probably fail.

        expiry_fmt = dt.strftime("%d%b%y").upper()

        try:
            strike_int = int(float(strike))
        except Exception:
            strike_int = strike

        return f"NIFTY{expiry_fmt}{option_type[0].upper()}{strike_int}"

    def select_option(self, price, position_type):
        expiry = get_weekly_expiry()
        if position_type == "CALL":
            strike = self.round_strike(price, "OTM_CALL")
        elif position_type == "PUT":
            strike = self.round_strike(price, "OTM_PUT")
        else:
            raise ValueError("Invalid position_type")

        symbol = self.get_symbol(strike, expiry, position_type)

        option_contract = {
            "strike": strike,
            "type": position_type,
            "expiry": expiry,
            "symbol": symbol,
        }

        print(f"Selected option: {option_contract}")
        return option_contract

    # Placeholder: assumes you have a dict self.option_prices with keys (strike, type, expiry)
    def get_option_prices(self, strike, expiry):
        # Try to use API if available
        if self.api_service:
            for opt_type in ("C", "P"):
                try:
                    api_data = self.api_service.get_options(strike, expiry, opt_type)
                except Exception:
                    api_data = None

                if not api_data:
                    continue

                # try to parse common shapes: list under 'data' / 'options' or top-level list
                items = []
                if isinstance(api_data, dict):
                    if isinstance(api_data.get("options"), list):
                        items = api_data["options"]
                    elif isinstance(api_data.get("data"), list):
                        items = api_data["data"]
                    else:
                        # gather lists contained in dict values
                        for v in api_data.values():
                            if isinstance(v, list):
                                items = v
                                break
                elif isinstance(api_data, list):
                    items = api_data

                # parse items into self.option_prices mapping
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    # attempt to read strike
                    s_strike = None
                    if "strike" in it:
                        try:
                            s_strike = int(it["strike"])
                        except Exception:
                            pass
                    # attempt to parse from symbol like NIFTY28OCT25C26000
                    if (
                        s_strike is None
                        and "symbol" in it
                        and isinstance(it["symbol"], str)
                    ):
                        m = re.search(r"(\d+)$", it["symbol"])
                        if m:
                            try:
                                s_strike = int(m.group(1))
                            except Exception:
                                s_strike = None

                    # type detection
                    typ = None
                    if "type" in it:
                        t = str(it["type"]).upper()
                        if "CALL" in t or t == "C":
                            typ = "CALL"
                        elif "PUT" in t or t == "P":
                            typ = "PUT"
                    elif "symbol" in it and isinstance(it["symbol"], str):
                        sym_up = it["symbol"].upper()
                        # look for C or P before the strike number in the symbol
                        m2 = re.search(r"[A-Z]+(\d+[A-Z]{3}\d{2})([CP])\d+$", sym_up)
                        if m2:
                            if "C" == m2.group(2):
                                typ = "CALL"
                            elif "P" == m2.group(2):
                                typ = "PUT"
                        else:
                            # fallback simple check
                            if "C" in sym_up:
                                typ = "CALL"
                            elif "P" in sym_up:
                                typ = "PUT"

                    # price detection: common keys ltp/last/price
                    price_val = None
                    for key in ("ltp", "last", "price", "lt"):
                        if key in it:
                            try:
                                price_val = float(it[key])
                                break
                            except Exception:
                                pass

                    if s_strike is not None and typ and price_val is not None:
                        # store using provided expiry parameter (best-effort)
                        self.option_prices[(s_strike, typ, expiry)] = price_val

        # Fallback to existing in-memory mapping
        call_price = self.option_prices.get((strike, "CALL", expiry), None)
        put_price = self.option_prices.get((strike, "PUT", expiry), None)
        return call_price, put_price
