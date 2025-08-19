import asyncio
import uuid  # for asynchronous operation
import websockets 
import json
import logging
from datetime import datetime
import ssl
import ocpp
# from update_status import StatusSimulator
import random
# from client.simulation import StationManager
import aiohttp
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s-%(name)s-%(levelname)s-%(message)s'
)

class Client:
    def __init__(self, charge_point_id, server_url="wss://localhost:8080", use_ssl=True):
        self.server_url = server_url
        self.charge_point_id = charge_point_id
        self.use_ssl = use_ssl
        self.heartbeat_task = None
        self.websocket = None
        self.last_message_time = datetime.now()
        self.heartbeat_interval = 60
        self.ssl_context = None
        if self.use_ssl:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self.ssl_context.check_hostname = False   # For self-signed certificate
            self.ssl_context.verify_mode = ssl.CERT_NONE
        self.status = 'Available'  # initial status to be shown
        self.connected = False  # connection status with server
        self.logger = logging.getLogger('Client')
        
    async def start(self):
        while True:
            try:
                await self.connect()
                break
            except Exception as e:
                self.logger.error(f"Connection error: {e}")
                await asyncio.sleep(5)
                self.logger.info("Reconnecting...")

    async def connect(self):
        protocol = "wss" if self.use_ssl else "ws"
        ssl_context = ssl._create_unverified_context()
        uri = f"wss://localhost:8080/{self.charge_point_id}"
        self.logger.info(f'Connecting to server... {uri}')
        
        try:
            # CORRECT - single connection
            self.websocket = await websockets.connect(
                uri,
                subprotocols=['ocpp1.6'],
                ssl=self.ssl_context if self.use_ssl else None,
                ping_interval=30,
                ping_timeout=10
            )
            self.connected = True
            self.logger.info(f'Client {self.charge_point_id} connected successfully: {uri}')

            # FIX: Send message in OCPP format
            await self.send_boot_notification()
                 
            # FIX: Call without parameters
            asyncio.create_task(self.heartbeat_loop())

            await self.send_status_notification(self.status)
            
            # FIX: Message listening loop
            await self.message_listener()

            asyncio.create_task(self.command_poll_loop())   # new
            asyncio.create_task(self.read_loop())    
            
        except Exception as e:
            self.logger.error(f'Connection error: {e}')
            self.connected = False

    # FIX: Message listener function
    async def message_listener(self):
        try:
            async for raw_message in self.websocket:
                await self.handle_messages(raw_message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            self.logger.error(f"Message listener error: {e}")
            self.connected = False

    async def handle_messages(self, raw_message: str):
        try:
            message = json.loads(raw_message)
            message_type = message[0]
            if message_type == 3:  # CALLRESULT
                payload = message[2] if len(message) > 2 else {}  # FIX: index 2, not 3
                self.logger.info(f"Response received: {payload}")
                if payload.get("status") == "Accepted" and payload.get("interval"):
                    self.heartbeat_interval = payload["interval"]
                elif payload.get("statyus") == "Accepted" and payload.get("interval"):  # Backup for server typo
                    self.heartbeat_interval = payload["interval"]
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    async def send_message(self, action: str, payload: dict) -> str:
        if self.websocket is None or not self.connected:
            return None
        message_id = str(uuid.uuid4())
        message = [2, message_id, action, payload]
        try:
            await self.websocket.send(json.dumps(message))
            self.last_message_time = datetime.now()
            return message_id
        except Exception as e:
            self.logger.error(f"Failed to send {action}: {e}")
            return None

    # FIX: Send message in OCPP format
    async def send_boot_notification(self):
        if self.websocket is None or not self.connected:
            return None
        boot_notification = {
            "cpId": self.charge_point_id,
            "chargePointVendor": "MyVendor",
            "chargePointModel": "MyModel",
            "chargePointSerialNumber": "1234567890",
            "chargeBoxSerialNumber": "9876543210",
            "firmwareVersion": "1.0.0",
            "iccid": "89012345678901234",
            "imsi": "123456789012345",
            "meterType": "MyMeterType",
            "meterSerialNumber": "1234567890"
        }
        await self.send_message("BootNotification", boot_notification)
        self.logger.info('BootNotification sent...')

    # FIX: Send single heartbeat, removed infinite loop
    async def send_heartbeat(self):
        heartbeat = {}  
        await self.send_message("Heartbeat", heartbeat)  # FIX: Send in OCPP format
        self.logger.info("Heartbeat sent...")
        
    # FIX: Send message in OCPP format
    async def send_status_notification(self, status):
        if self.websocket is None or not self.connected:
            self.logger.warning("Client is not connected..")
            return
        self.status = status
        self.send_heartbeat_flag = (status == "Available")
        status_notification = {
            "cpId": self.charge_point_id,
            "connectorId": 0,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.send_message("StatusNotification", status_notification)
        self.logger.info(f"StatusNotification: {status}")

    async def heartbeat_loop(self):
        while self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.connected and self.status == 'Available':
                    await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                break

    async def command_poll_loop(self):
        base = "http://localhost:3000"
        while True:
            try:
                url = f"{base}/next_command/{self.charge_point_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            cmd = data.get("command")
                            if cmd:
                                await self._handle_command(cmd)
            except Exception as e:
                logging.error(f"Command poll error: {e}")
                await asyncio.sleep(1.5)

    async def _handle_command(self, cmd: str):
        cmd = cmd.lower().strip()
        status_map = {
            "start": "Charging",
            "suspend": "SuspendedEV", 
            "finish": "Available"
        }
        new_status = status_map.get(cmd)
        if new_status:
            await self.send_status_notification(new_status)

    async def _send_call(self, action, payload):
        # USE THE EXISTING TEMPLATE YOU ALREADY HAVE: generate msg_id, send [2, id, action, payload]
        msg_id = self._next_msg_id()
        frame = [2, msg_id, action, payload]
        await self.websocket.send(json.dumps(frame))
        # (If needed, wait for CallResult, here skipped)
 
async def main():
    client_ids = ["EVC_1", "EVC_2", "EVC_3"]
    tasks = []
    for cid in client_ids:
        client = Client(cid)
        tasks.append(asyncio.create_task(client.start()))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
