from config import FlattradeConfig
from auth import FlattradeAuth
from positions import PositionsService
from commands import CommandHandler, GetPositionsCommand
from typing import Any


class FlattradeClient:
    def __init__(self, config: FlattradeConfig):
        self.config = config
        self.auth = FlattradeAuth(config)
        self._token = None
        self._positions_service = None
        self.command_handler = CommandHandler()
        self._initialize()

    def _get_token(self) -> str:
        """Get authentication token, either from config or by authenticating."""
        if self.config.FINAL_TOKEN:
            return self.config.FINAL_TOKEN

        request_code = self.auth.get_request_code()
        return self.auth.get_api_token(request_code)

    def _initialize(self) -> None:
        """Initialize client with config validation and token."""
        self.config.validate()
        self._token = self._get_token()
        self._positions_service = PositionsService(self.config, self._token)
        self.command_handler.register_command("get_positions", GetPositionsCommand(self))

    def get_positions(self):
        """Get current positions."""
        return self._positions_service.get_positions()

    def execute(self, command_name: str) -> Any:
        """Execute a command by name."""
        return self.command_handler.execute_command(command_name)


def main():
    """Main entry point for the application."""
    config = FlattradeConfig()
    client = FlattradeClient(config)
    client.execute("get_positions")


if __name__ == "__main__":
    main() 