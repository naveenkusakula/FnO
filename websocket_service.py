import asyncio
import json
import ssl

import websockets

from config import Config


class WebSocketService:

    def __init__(self, config: Config, auth_token: str):
        self.config = config
        self.auth_token = auth_token
        self.websocket = None
        self.connected = False
        self.last_update_time = None
        self.timeout_seconds = config.WS_TIMEOUT_SECONDS
        self._listening = False

    async def connect(self) -> bool:
        try:
            uri = "wss://piconnect.flattrade.in/PiConnectWSTp/"
            print(f"Attempting to connect to {uri}")

            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self.websocket = await websockets.connect(uri, ssl=ssl_context)
            print("WebSocket connection established")

            connect_message = {"t": "c",  # connect task
                "uid": self.config.CLIENT_ID, "actid": self.config.CLIENT_ID, "source": "API",
                "susertoken": self.auth_token}
            print(f"Sending connection request: {connect_message}")

            await self.websocket.send(json.dumps(connect_message))

            response = await self.websocket.recv()
            response_data = json.loads(response)
            print(f"Received response: {response_data}")

            if response_data.get("t") == "ck" and response_data.get("s") == "OK":
                self.connected = True
                self.last_update_time = asyncio.get_event_loop().time()
                print("WebSocket connection established successfully")
                return True
            else:
                print(f"WebSocket connection failed: {response_data}")
                return False

        except Exception as e:
            print(f"Error connecting to WebSocket: {e}")
            return False

    async def subscribe_nifty(self) -> bool:
        if not self.connected:
            print("WebSocket not connected")
            return False

        try:
            subscribe_message = {"t": "t", "k": "NSE|26000"}

            print("Subscribing to NIFTY...")
            await self.websocket.send(json.dumps(subscribe_message))

            response = await self.websocket.recv()
            response_data = json.loads(response)
            print(f"Received NIFTY subscription acknowledgment: {response_data}")

            if response_data.get("t") == "tk":
                print(f"Successfully subscribed to NIFTY")
                return True
            else:
                print(f"Failed to subscribe to NIFTY: {response_data}")
                return False

        except Exception as e:
            print(f"Error subscribing to NIFTY: {e}")
            return False

    async def listen(self) -> None:
        if not self.connected:
            print("WebSocket not connected")
            return

        print("\nStarting to listen for WebSocket messages...")
        self._listening = True
        try:
            while self._listening and self.connected:
                try:
                    print("Waiting for message...")
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    message_type = data.get("t")

                    self.last_update_time = asyncio.get_event_loop().time()

                    if message_type == "tf":
                        print(f"\nNIFTY Update:")
                        print(f"LTP: {data.get('lp')}, Change: {data.get('pc')}%")
                    else:
                        print(f"Received message of type: {message_type}")
                        print(f"Full message data: {data}")

                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    self.connected = False
                    break
                except Exception as e:
                    print(f"Error in WebSocket listener: {e}")
                    print(f"Error type: {type(e)}")
                    break

        finally:
            self._listening = False
            print("Stopped listening for WebSocket messages")

    async def disconnect(self) -> None:
        self._listening = False
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("WebSocket connection closed")

    async def check_timeout(self) -> None:
        while self.connected:
            current_time = asyncio.get_event_loop().time()
            if self.last_update_time and (current_time - self.last_update_time) > self.timeout_seconds:
                print(f"No updates received for {self.timeout_seconds} seconds. Stopping the program.")
                self.connected = False
                if self.websocket:
                    await self.websocket.close()
                break
            await asyncio.sleep(1)
