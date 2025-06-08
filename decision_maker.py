import pandas as pd


class DecisionMaker:
    def __init__(self, ema_short=5, ema_long=15):
        self.prices = []
        self.ema_short_span = ema_short
        self.ema_long_span = ema_long
        self.position = None

    def update_price(self, price):
        self.prices.append(price)
        if len(self.prices) > 100:
            self.prices.pop(0)

    def calculate_signal(self):
        if len(self.prices) < self.ema_long_span:
            return "HOLD"

        price_series = pd.Series(self.prices)
        ema_short = price_series.ewm(span=self.ema_short_span, adjust=False).mean().iloc[-1]
        ema_long = price_series.ewm(span=self.ema_long_span, adjust=False).mean().iloc[-1]

        print(f"EMA{self.ema_short_span}: {ema_short:.2f}, EMA{self.ema_long_span}: {ema_long:.2f}")

        if ema_short > ema_long:
            return "BUY_CALL"
        elif ema_short < ema_long:
            return "BUY_PUT"
        else:
            return "HOLD"

    def execute_trade(self, signal):
        if signal == "BUY_CALL" and self.position != "CALL":
            print(">> BUY CALL signal")
            self.position = "CALL"
            # place buy CE order
        elif signal == "BUY_PUT" and self.position != "PUT":
            print(">> BUY PUT signal")
            self.position = "PUT"
            # place buy PE order
        else:
            print(">> HOLD / no action")
