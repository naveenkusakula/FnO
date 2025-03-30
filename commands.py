from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Command(ABC):
    """Base command class for all Flattrade operations."""

    @abstractmethod
    def execute(self) -> Any:
        """Execute the command and return its result."""
        pass


class GetPositionsCommand(Command):
    """Command to fetch current positions from Flattrade."""

    def __init__(self, client):
        """Initialize the command with a FlattradeClient instance."""
        self.client = client

    def execute(self) -> Optional[Dict]:
        """Execute the command to fetch positions."""
        try:
            positions = self.client.get_positions()
            if positions:
                print("Current Positions:", positions)
            return positions
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return None


class CommandHandler:
    """Handles registration and execution of commands."""

    def __init__(self):
        """Initialize the command handler with an empty command registry."""
        self.commands: Dict[str, Command] = {}

    def register_command(self, name: str, command: Command) -> None:
        """Register a new command with the handler."""
        self.commands[name] = command

    def execute_command(self, name: str) -> Any:
        """Execute a command by its registered name."""
        command = self.commands.get(name)
        if not command:
            raise ValueError(f"Command '{name}' not found")
        return command.execute() 