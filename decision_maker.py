from options_service import OptionsService
import pandas as pd


class DecisionMaker:
    def __init__(
        self,
        ema_short=5,
        ema_long=15,
        stop_loss_pct=0.05,
        target_profit_pct=0.10,
        enable_momentum_filter=True,
        ema_diff_threshold=0.0005,
        price_momentum_threshold=0.0005,
        max_loss_amt=500,
        min_profit_amt=250,
        lot_size=25,
        options_service=None,
        api_service=None,
    ):
        self.option_service = options_service or OptionsService()
        self.api_service = api_service
        self.prices = []
        self.ema_short_span = ema_short
        self.ema_long_span = ema_long
        self.position = None
        self.entry_price = None
        self.current_symbol = None
        self.current_qty = 0
        self.stop_loss_pct = stop_loss_pct
        self.target_profit_pct = target_profit_pct
        self.enable_momentum_filter = enable_momentum_filter
        self.ema_diff_threshold = ema_diff_threshold
        self.price_momentum_threshold = price_momentum_threshold
        self.max_loss_amt = max_loss_amt
        self.min_profit_amt = min_profit_amt
        self.lot_size = lot_size

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
        expiry = (
            self.option_service.get_weekly_expiry()
            if hasattr(self.option_service, "get_weekly_expiry")
            else None
        )
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
            print(
                f"Put-Call Parity Arbitrage Opportunity: market={market_value:.2f}, parity={parity_value:.2f}"
            )
            return "ARBITRAGE"
        return None

    def calculate_ema_signal(self):
        if len(self.prices) < self.ema_long_span + 5:
            return None

        # Create pandas Series
        price_series = pd.Series(self.prices)

        # Calculate EMAs
        ema_short = price_series.ewm(span=self.ema_short_span, adjust=False).mean()
        ema_long = price_series.ewm(span=self.ema_long_span, adjust=False).mean()

        # Get last two values
        curr_short = ema_short.iloc[-1]
        curr_long = ema_long.iloc[-1]
        prev_short = ema_short.iloc[-2]
        prev_long = ema_long.iloc[-2]

        # Bullish Crossover (Golden Cross)
        if prev_short <= prev_long and curr_short > curr_long:
            print(
                f"EMA Bullish Crossover: Short({curr_short:.2f}) > Long({curr_long:.2f})"
            )
            return "BUY_CALL"

        # Bearish Crossover (Death Cross)
        if prev_short >= prev_long and curr_short < curr_long:
            print(
                f"EMA Bearish Crossover: Short({curr_short:.2f}) < Long({curr_long:.2f})"
            )
            return "BUY_PUT"

        return None

    def calculate_signal(self):
        # 1. EMA Signal (Directional)
        ema_signal = self.calculate_ema_signal()
        if ema_signal:
            return ema_signal

        # 2. Check for Put-Call Parity arbitrage (Secondary)
        arb_signal = self.check_put_call_parity_arb()
        if arb_signal == "ARBITRAGE":
            # Currently we don't have logic to execute ARBITRAGE
            pass

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

        symbol = selected_option.get("symbol")
        qty = self.lot_size  # Default quantity, consider making this configurable

        success = False
        if self.api_service and symbol:
            resp = self.api_service.place_order(
                symbol=symbol,
                qty=qty,
                transaction_type="B",
                price_type="MKT",  # Market order for entry
                product_type="M",
            )
            if resp and resp.get("stat") == "Ok":
                print(f">> Order Placed Successfully: {resp.get('nordno')}")
                success = True
            else:
                print(f">> Order Failed: {resp}")
        else:
            print(">> Dry Run / No API Service")
            success = True  # Treat as success for simulation if no API

        if success:
            self.position = position_type
            self.entry_price = price
            self.current_symbol = symbol
            self.current_qty = qty
            print(
                ">> Entering position:",
                self.position,
                "at",
                self.entry_price,
                "Symbol:",
                symbol,
            )

    def check_exit(self, current_price):
        if self.position is None or self.entry_price is None:
            return

        # Estimate Option PnL based on Spot Move
        # Assumption: ATM Delta ~ 0.5
        delta = 0.5
        spot_change = current_price - self.entry_price

        if self.position == "PUT":
            spot_change *= -1

        estimated_pnl_per_qty = spot_change * delta
        total_estimated_pnl = estimated_pnl_per_qty * self.current_qty

        # Scale thresholds by number of lots
        # Avoid division by zero if lot_size is Somehow 0
        lot_count = 1
        if self.lot_size > 0:
            lot_count = self.current_qty / self.lot_size

        scaled_min_profit = self.min_profit_amt * lot_count
        scaled_max_loss = self.max_loss_amt * lot_count

        change_pct = (
            spot_change
        ) / self.entry_price  # This is Spot % change, not Option % change

        should_exit = False
        exit_reason = ""

        # Check PnL against amount thresholds
        if total_estimated_pnl >= scaled_min_profit:
            should_exit = True
            exit_reason = f"TARGET HIT (Est. PnL: ₹{total_estimated_pnl:.2f} >= ₹{scaled_min_profit:.2f})"

        elif total_estimated_pnl <= -scaled_max_loss:
            should_exit = True
            exit_reason = f"STOP LOSS HIT (Est. PnL: ₹{total_estimated_pnl:.2f} <= -₹{scaled_max_loss:.2f})"

        # Keep percentage check as backup (e.g. if Spot moves 10%)
        elif change_pct >= self.target_profit_pct:
            should_exit = True
            exit_reason = f"TARGET PCT HIT (Spot Change: {change_pct:.2%})"
        elif change_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = f"STOP LOSS PCT HIT (Spot Change: {change_pct:.2%})"

        if should_exit:
            print(f">> SELL {self.position} at {current_price} — {exit_reason}")

            success = False
            if self.api_service and self.current_symbol:
                resp = self.api_service.place_order(
                    symbol=self.current_symbol,
                    qty=self.current_qty,
                    transaction_type="S",
                    price_type="MKT",
                    product_type="M",
                )
                if resp and resp.get("stat") == "Ok":
                    print(f">> Exit Order Placed: {resp.get('nordno')}")
                    success = True
                else:
                    print(f">> Exit Order Failed: {resp}")
            else:
                print(">> Dry Run Exit")
                success = True

            if success:
                self.reset_position()

    def reset_position(self):
        self.position = None
        self.entry_price = None
        self.current_symbol = None
        self.current_qty = 0
