from typing import Dict, Optional

import requests
from config import FlattradeConfig


class PositionsService:
    """Service for handling position-related operations with Flattrade."""

    def __init__(self, config: FlattradeConfig, auth_token: str):
        """Initialize the positions service."""
        self.config = config
        self.auth_token = auth_token

    def get_positions(self) -> Optional[Dict]:
        """Fetch current positions from Flattrade."""
        payload = (
            f"jData={{\n\t\"uid\": \"{self.config.CLIENT_ID}\",\n\t\"actid\": \"{self.config.CLIENT_ID}\"\n}}"
            f"&jKey={self.auth_token}"
        )
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/11.0.1",
        }

        try:
            response = requests.request("POST", self.config.POSITIONS_URL, data=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            print(f"Error fetching positions: {response.status_code}, {response.text}")
            return None
        except Exception as e:
            print(f"Exception while fetching positions: {e}")
            return None 