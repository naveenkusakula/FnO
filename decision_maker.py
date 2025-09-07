import pandas as pd

from options_service import OptionsService


class DecisionMaker:
    def __init__(self, ema_short=5, ema_long=15,
                 stop_loss_pct=0.05, target_profit_pct=0.10,
                 enable_momentum_filter=True,
                 ema_diff_threshold=0.0005, price_momentum_threshold=0.0005,
                 max_loss_amt=500, min_profit_amt=250, options_service=None):
        self.option_service = options_service or OptionsService()
        self.prices = []
        self.ema_short_span = ema_short
        self.ema_long_span = ema_long
        self.position = None
        self.entry_price = None
        self.stop_loss_pct = stop_loss_pct
        self.target_profit_pct = target_profit_pct
        self.enable_momentum_filter = enable_momentum_filter
        self.ema_diff_threshold = ema_diff_threshold
        self.price_momentum_threshold = price_momentum_threshold
        self.max_loss_amt = max_loss_amt
        self.min_profit_amt = min_profit_amt

    def update_price(self, price):
        self.prices.append(price)
        if len(self.prices) > 100:
            self.prices.pop(0)

        self.check_exit(price)  # Check if we should sell

    def check_put_call_parity_arb(self):
        if len(self.prices) == 0:
            return None
        spot_price = self.prices[-1]
        strike = self.option_service.round_strike(spot_price, "ATM")
        expiry = self.option_service.get_weekly_expiry() if hasattr(self.option_service, 'get_weekly_expiry') else None
        if expiry is None:
            from options_service import get_weekly_expiry
            expiry = get_weekly_expiry()
        call_price, put_price = self.option_service.get_option_prices(strike, expiry)
        if call_price is None or put_price is None:
            return None
        # Put-Call Parity: C - P = S - K * exp(-rT)
        # For simplicity, assume r ~ 0 and T is small, so C - P ≈ S - K
        parity_value = spot_price - strike
        market_value = call_price - put_price
        arb_threshold = 2  # You can adjust this threshold
        if abs(market_value - parity_value) > arb_threshold:
            print(f"Put-Call Parity Arbitrage Opportunity: market={market_value:.2f}, parity={parity_value:.2f}")
            return "ARBITRAGE"
        return None

    def calculate_signal(self):
        # Check for Put-Call Parity arbitrage first
        arb_signal = self.check_put_call_parity_arb()
        if arb_signal:
            return arb_signal
        return None

    def execute_trade(self, price):
        signal = self.calculate_signal()

        if signal == "BUY_CALL" and self.position != "CALL":
            self.enter_trade("CALL", price)

        elif signal == "BUY_PUT" and self.position != "PUT":
            self.enter_trade("PUT", price)


    def enter_trade(self, position_type, price):
        selected_option = self.option_service.select_option(price, position_type)
        print(f"BUY {position_type} Option: {selected_option}")
        self.position = position_type
        self.entry_price = price
        print(">> Entering position:", self.position, "at", self.entry_price)
        # Add actual order logic here (e.g., API call)

    def check_exit(self, current_price):
        if self.position is None or self.entry_price is None:
            return

        change_pct = (current_price - self.entry_price) / self.entry_price
        pnl = current_price - self.entry_price

        if self.position == "PUT":
            change_pct *= -1
            pnl *= -1

        if change_pct >= self.target_profit_pct or pnl >= self.min_profit_amt:
            print(f">> SELL {self.position} at {current_price} — 🎯 target hit ({change_pct:.2%}, ₹{pnl:.2f})")
            self.reset_position()
            # todo
            # Add actual sell order here

        elif change_pct <= -self.stop_loss_pct or pnl <= -self.max_loss_amt:
            print(f">> SELL {self.position} at {current_price} — 🛑 stop loss hit ({change_pct:.2%}, ₹{pnl:.2f})")
            self.reset_position()
            # todo
            # Add actual sell order here

    def reset_position(self):
        self.position = None
        self.entry_price = None
