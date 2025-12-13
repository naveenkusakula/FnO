import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock
from decision_maker import DecisionMaker
from options_service import OptionsService
from get_api_service import GetApiService
from config import Config


class TestDecisionMaker(unittest.TestCase):
    def setUp(self):
        # Mock Config
        self.config = MagicMock(spec=Config)
        self.config.CLIENT_ID = "TEST_CLIENT"
        self.config.PLACE_ORDER_URL = "http://mock-url"

        # Mock Services
        self.api_service = MagicMock(spec=GetApiService)
        self.api_service.config = self.config
        # We need place_order to return a success response
        self.api_service.place_order.return_value = {"stat": "Ok", "nordno": "12345"}

        self.options_service = MagicMock()
        self.options_service.get_weekly_expiry.return_value = "28-OCT-2025"
        self.options_service.round_strike.return_value = 26000

        def select_option_side_effect(price, position_type):
            symbol = f"NIFTY28OCT25{'C' if position_type == 'CALL' else 'P'}26000"
            return {
                "strike": 26000,
                "type": position_type,
                "expiry": "28-OCT-2025",
                "symbol": symbol,
            }

        self.options_service.select_option.side_effect = select_option_side_effect

        # For arbitrage check
        self.options_service.get_option_prices.return_value = (100, 50)

        self.dm = DecisionMaker(
            options_service=self.options_service,
            api_service=self.api_service,
            lot_size=25,
        )

    def test_enter_trade(self):
        print("\n--- Testing Enter Trade ---")
        # Simulate a BUY signal
        self.dm.enter_trade("CALL", 25900)

        # Check if place_order was called
        self.api_service.place_order.assert_called_once()
        call_args = self.api_service.place_order.call_args[1]
        print(f"Call Args: {call_args}")

        self.assertEqual(call_args["symbol"], "NIFTY28OCT25C26000")
        self.assertEqual(call_args["transaction_type"], "B")
        self.assertEqual(call_args["qty"], 25)

        self.assertEqual(self.dm.position, "CALL")
        self.assertEqual(self.dm.current_symbol, "NIFTY28OCT25C26000")

    def test_exit_trade_target(self):
        print("\n--- Testing Exit Trade (Target) ---")
        # Set up a position
        self.dm.position = "CALL"
        self.dm.entry_price = 100
        self.dm.current_symbol = "NIFTY28OCT25C26000"
        self.dm.current_qty = 25
        self.dm.target_profit_pct = 0.1  # 10%

        # Update price to hit target (100 + 10% = 110)
        self.dm.check_exit(115)

        # Check if place_order was called for SELL
        self.api_service.place_order.assert_called_once()
        call_args = self.api_service.place_order.call_args[1]
        print(f"Exit Call Args: {call_args}")

        self.assertEqual(call_args["transaction_type"], "S")
        self.assertEqual(call_args["symbol"], "NIFTY28OCT25C26000")

        # Check if position reset
        self.assertIsNone(self.dm.position)

    def test_exit_trade_stop_loss(self):
        print("\n--- Testing Exit Trade (Stop Loss) ---")
        # Set up a position
        self.dm.position = "PUT"
        self.dm.entry_price = 100
        self.dm.current_symbol = "NIFTY28OCT25P26000"
        self.dm.current_qty = 25
        self.dm.stop_loss_pct = 0.05  # 5%

        # For PUT, stop loss is when price goes DOWN (wait, PUT value goes UP when spot goes DOWN.
        # The DecisionMaker `check_exit` logic assumes `current_price` is the underlying spot price?
        # Let's check `decision_maker.py`.
        # `update_price` calls `check_exit(price)`. `price` is appended to `self.prices`.
        # Usually `decision_maker` tracks SPOT price.
        # But `check_exit` calculates: `pnl = current_price - self.entry_price`.
        # IF `current_price` is SPOT price, calculating PnL directly from Spot Price difference is an approximation (Delta=1).
        # However, `enter_trade` stores `entry_price` as the passed `price`.
        # This implies `DecisionMaker` currently assumes it trades the Spot/Future itself OR uses Delta=1.
        # It's a simplistic logic.
        # IF it means `current_price` is the PREMIUM of the option, then `update_price` must be fed Option premiums.
        # But `update_price` is likely fed Spot prices from `SubscribeNiftyCommand`.
        # `SubscribeNiftyCommand` listens to Nifty.
        # So `DecisionMaker` is mixing Spot Price logic with Option PnL?
        # Re-reading `decision_maker.py`:
        # `if self.position == "PUT": change_pct *= -1; pnl *= -1`
        # This confirms it uses Spot Price movements to estimate PnL.
        # So if I bought PUT at Spot=100.
        # If Spot goes to 110. change = (110-100)/100 = 10%. PUT logic flips it to -10%. Stop loss.

        # Test Case: Spot rises, PUT loses value -> Stop Loss.
        self.dm.check_exit(110)

        self.api_service.place_order.assert_called_once()
        self.assertEqual(
            self.api_service.place_order.call_args[1]["transaction_type"], "S"
        )
        self.assertIsNone(self.dm.position)

    def test_ema_crossover_call(self):
        print("\n--- Testing EMA Crossover (Golden Cross -> BUY CALL) ---")
        # Setup: EMA Short=5, Long=15
        # We need a series of prices where short > long eventually

        # Start with a downtrend or flat to establish EMAs
        prices = [100.0] * 20
        # Then ramp up quickly to pull Short EMA above Long EMA
        prices += [101, 102, 103, 104, 105, 106, 110, 115, 120]

        for p in prices:
            self.dm.update_price(p)
            self.dm.execute_trade(p)

        # We expect a CALL to be bought at some point during the ramp up
        self.api_service.place_order.assert_called()

        # Check if any call was a BUY
        buy_order_found = False
        for call in self.api_service.place_order.call_args_list:
            args = call[1]
            if args["transaction_type"] == "B" and "C" in args["symbol"]:
                buy_order_found = True
                print(f"Found BUY CALL order: {args}")
                break

        self.assertTrue(buy_order_found, "Did not find a BUY CALL order")

        # Verify position was entered (even if exited later, checking logic flow)
        # Note: If it exited, self.dm.position would be None.
        # So we trust the API call verification.

    def test_ema_crossover_put(self):
        print("\n--- Testing EMA Crossover (Death Cross -> BUY PUT) ---")
        # Reset
        self.dm.reset_position()
        self.dm.prices = []
        self.api_service.place_order.reset_mock()

        # Start high
        prices = [150.0] * 20
        # Drop quickly
        prices += [149, 148, 147, 146, 140, 130, 120]

        for p in prices:
            self.dm.update_price(p)
            self.dm.execute_trade(p)

        self.api_service.place_order.assert_called()

        # Check if any call was a BUY
        buy_order_found = False
        for call in self.api_service.place_order.call_args_list:
            args = call[1]
            if args["transaction_type"] == "B" and "P" in args["symbol"]:
                buy_order_found = True
                print(f"Found BUY PUT order: {args}")
                break

        self.assertTrue(buy_order_found, "Did not find a BUY PUT order")


if __name__ == "__main__":
    unittest.main()
