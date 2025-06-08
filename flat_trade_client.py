from config import Config
from auth import Auth
from positions_service import PositionsService
from commands import CommandHandler, GetPositionsCommand, SubscribeNiftyCommand
from typing import Any, Dict, Optional
from decision_maker import DecisionMaker
import asyncio


class FlatTradeClient:

    def __init__(self, config: Config):
        self.config = config
        self.auth = Auth(config)
        self._token = None
        self._positions_service = None
        self.command_handler = CommandHandler()
        self.trader = DecisionMaker()
        self._initialize()

    def _get_token(self) -> str:
        try:
            if self.config.FINAL_TOKEN:
                print("Using token from environment variables: " + self.config.FINAL_TOKEN)
                return self.config.FINAL_TOKEN
            else:
                print("No token found in environment, fetching new token")
                request_code = self.auth.get_request_code()
                print(f"Got request code: {request_code}")
                token = self.auth.get_api_token(request_code)
                print(f"Got API token: {token}")
                return token

        except Exception as e:
            print(f"Error getting token: {e}")
            raise

    def _initialize(self) -> None:
        self.config.validate()
        self._token = self._get_token()
        self._positions_service = PositionsService(self.config, self._token)
        self.command_handler.register_command("get_positions", GetPositionsCommand(self))
        self.command_handler.register_command("subscribe-nifty50", SubscribeNiftyCommand(self))

    def get_positions(self) -> Optional[Dict]:
        if not self._positions_service:
            raise ValueError("Positions service not initialized")
        return self._positions_service.get_positions()

    def execute(self, command_name: str) -> Any:
        command = self.command_handler.commands.get(command_name)
        if not command:
            raise ValueError(f"Command '{command_name}' not found")
        if command_name == "subscribe-nifty50":
            return asyncio.run(command.execute())
        return command.execute()


def main():
    config = Config()
    client = FlatTradeClient(config)
    client.execute("subscribe-nifty50")
    #client.execute("get_positions")


if __name__ == "__main__":
    main()
