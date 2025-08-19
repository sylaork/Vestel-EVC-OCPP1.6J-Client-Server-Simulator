import asyncio
import json
import logging
import websockets
from datetime import datetime
from pathlib import Path
import ssl
# libraries for REST API 
import aiohttp  # for sending asynchronous HTTP requests to REST API
import os
from collections import OrderedDict
import sqlite3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s-%(name)s-%(levelname)s:%(message)s'
)


class Server:
    def __init__(self, host='localhost', port=8080, use_ssl='True'):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.logger = logging.getLogger('Server')
        self.connections = {}
        self.rest_base = os.environ.get('REST_API_BASE', 'http://localhost:3000')  # REST API base URL (Flask)

    async def _post_to_rest(self, endpoint: str, payload: dict):  # send POST request to REST API
        url = f"{self.rest_base.rstrip('/')}/{endpoint.lstrip('/')}"  # remove trailing/leading slashes
        try:
            timeout = aiohttp.ClientTimeout(total=5)  # set timeout to 5 seconds
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # log payload (can be removed later)
                self.logger.info(f'[REST]-> {endpoint} payload: {json.dumps(payload, ensure_ascii=False)}')

                async with session.post(url, json=payload) as response:  # payload is automatically converted to JSON
                    text = await response.text()  # read response from server
                    if response.status >= 400:
                        self.logger.error(f'Restapi error: [REST]{endpoint}-> {response.status}{text}')
                    else:
                        self.logger.info(f'[REST] OK {endpoint}-> {response.status}')

        except Exception as e:
            self.logger.error(f'[REST] POST {endpoint} failed {e}')

    async def _log_action_to_rest(self, cp_id: str, action: str, payload: dict):
        # When sending to REST without touching OCPP schema, cpID is added at the beginning
        # Every endpoint receives JSON that starts with cpID (using OrderedDict)

        if action == 'BootNotification':
            body = OrderedDict([
                ("cpId", cp_id),
                ("chargePointVendor",       payload.get("chargePointVendor")),
                ("chargePointModel",        payload.get("chargePointModel")),
                ("chargePointSerialNumber", payload.get("chargePointSerialNumber")),
                ("chargeBoxSerialNumber",   payload.get("chargeBoxSerialNumber")),
                ("firmwareVersion",         payload.get("firmwareVersion")),
                ("iccid",                   payload.get("iccid")),
                ("imsi",                    payload.get("imsi")),
                ("meterType",               payload.get("meterType")),
                ("meterSerialNumber",       payload.get("meterSerialNumber")),
            ])
            await self._post_to_rest('/bootnotification', body)

            # This is the first connection message where the charging station introduces itself

        elif action == 'Heartbeat':
            body = OrderedDict([
                ('cpId', cp_id),
                ('currentTime', payload.get("currentTime")),
            ])
            await self._post_to_rest('/heartbeat', body)

        elif action == 'StatusNotification':
            body = OrderedDict([
                ('cpId', cp_id),
                ('connectorId', payload.get("connectorId")),
                ('status', payload.get("status")),
                ('errorCode', payload.get("errorCode")),
                ('info', payload.get("info")),
                ('timestamp', payload.get("timestamp")),
                ('vendorId', payload.get("vendorId")),
                ('vendorErrorCode', payload.get("vendorErrorCode")),
            ])
            await self._post_to_rest('/statusnotification', body)

        else:
            self.logger.debug(f'[REST] unknown action {action}')  # if not one of the 3 supported messages, do not send to REST

    async def start(self):
        protocol = 'wss' if self.use_ssl else 'ws'
        self.logger.info(f'Server starting: {protocol}://{self.host}:{self.port}')

        ssl_context = None
        if self.use_ssl:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            # assuming cert and key are in the same directory
            ssl_cert = Path("cert.pem")
            ssl_key = Path("key.pem")
            if not ssl_cert.exists() or not ssl_key.exists():
                self.logger.error("SSL certificate or key file not found!")
                raise FileNotFoundError("cert.pem or key.pem not found in current directory.")
            ssl_context.load_cert_chain(str(ssl_cert), str(ssl_key))

        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            subprotocols=['ocpp1.6'],
            ssl=ssl_context
        ):
            self.logger.info(f'Server started: {protocol}://{self.host}:{self.port}')
            await asyncio.Future()

    async def handle_client(self, websocket, path):  # the URL path used by the client
        charge_point_id = path.strip('/')  # extract station ID from URL
        client_address = websocket.remote_address  # returns (ip, port) of connected client
        self.logger.info(f'Client connected: {charge_point_id} from {client_address}')
        self.connections[charge_point_id] = websocket
        # important for knowing which IP is connected, unique IDs help distinguish clients

        try:
            async for message in websocket:
                await self.handle_message(websocket, charge_point_id, message)
                '''
                 # Loop works like this:
                 while client_connected:
                     wait_for_message()
                     msg = receive_message_from_websocket()
                     call_handle_message(msg)
                '''
        except websocket.exceptions.ConnectionClosed:  # until client disconnects, keep running
            self.logger.info(f'Client disconnected: {charge_point_id}')
        finally:
            self.connections.pop(charge_point_id, None)  # remove client when disconnected (None prevents KeyError)

    async def handle_message(self, websocket, charge_point_id, raw_message):
        try:
            message = json.loads(raw_message)
            # OCPP messages always have 4 elements
            message_type = message[0]  # type of OCPP message
            message_id = message[1]    # ID of OCPP message
            action = message[2]        # action of OCPP message
            payload = message[3] if len(message) > 3 else {}  # payload of OCPP message (safe parsing)
            # len check: OCPP message must have min 3 elements, payload is optional
            self.logger.info(f"[{charge_point_id}] Received {action}: {payload}")

            if message_type == 2:  # CALL
                response = await self.process_call(action, payload)
                response_message = [3, message_id, response]

                await websocket.send(json.dumps(response_message))
                self.logger.info(f"[{charge_point_id}] processed {action}: {payload}")
                # send to REST API asynchronously
                asyncio.create_task(self._log_action_to_rest(charge_point_id, action, payload))

        except Exception as e:
            self.logger.error(f'Message processing error: {charge_point_id} - {e}')

    async def process_call(self, action, payload):  # takes a CALL and returns a CALLRESULT
        if action == 'BootNotification':
            return {
                'status': 'Accepted',
                'currentTime': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'interval': 60  # heartbeat interval
            }
        elif action == 'Heartbeat':
            return {
                'currentTime': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            }
        elif action == 'StatusNotification':  # empty response is enough, just acknowledgment
            return {}
        else:
            self.logger.warning(f'Unknown action: {action}')  # if client sends unsupported action
            return {}  # prevents crashing

async def main():
    server = Server(host='localhost', port=8080, use_ssl=True)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
