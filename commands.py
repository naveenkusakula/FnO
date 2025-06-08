from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from decision_maker import DecisionMaker

from web_socket_service import WebSocketService


class Command(ABC):

    @abstractmethod
    def execute(self) -> Any:
        pass


class GetPositionsCommand(Command):

    def __init__(self, client):
        self.client = client

    def execute(self) -> Optional[Dict]:
        try:
            positions = self.client.get_positions()
            if positions:
                print("Current Positions:", positions)
            return positions
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return None


class SubscribeNiftyCommand(Command):

    def __init__(self, client):
        self.client = client
        self.websocket_service = None

    async def execute(self) -> Any:
        try:
            dm = DecisionMaker()
            self.websocket_service = WebSocketService(self.client.config, self.client._token, dm)

            if not await self.websocket_service.connect():
                print("Failed to connect to WebSocket")
                return False

            if not await self.websocket_service.subscribe_nifty():
                print("Failed to subscribe to NIFTY")
                await self.websocket_service.disconnect()
                return False

            await self.websocket_service.listen()

        except Exception as e:
            print(f"Error in SubscribeNiftyCommand: {e}")
            return False
        finally:
            if self.websocket_service:
                await self.websocket_service.disconnect()
        return True


class CommandHandler:

    def __init__(self):
        self.commands: Dict[str, Command] = {}

    def register_command(self, name: str, command: Command) -> None:
        self.commands[name] = command

    def execute_command(self, name: str) -> Any:
        command = self.commands.get(name)
        if not command:
            raise ValueError(f"Command '{name}' not found")
        return command.execute()
