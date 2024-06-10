import asyncio
import websockets
import json
import hmac
import hashlib
from datetime import datetime

clientId = "kXV7l7Pe"
clientSecret = "cnvhFL3uFdU4YQvlSj6TR7KtbHZWg_g5YYt4rn-WkTw"
# timestamp = round(datetime.now().timestamp() * 1000)
# nonce = "abcd"
# data = ""
# signature = hmac.new(
#     bytes(clientSecret, "latin-1"),
#     msg=bytes('{}\n{}\n{}'.format(timestamp, nonce, data), "latin-1"),
#     digestmod=hashlib.sha256
# ).hexdigest().lower()

# msg = {
#     "jsonrpc": "2.0",
#     "id": 8748,
#     "method": "public/auth",
#     "params": {
#         "grant_type": "client_signature",
#         "client_id": clientId,
#         "timestamp": timestamp,
#         "signature": signature,
#         "nonce": nonce,
#         "data": data
#     }
# }

# print(msg)

# async def call_api(msg):
#     async with websockets.connect('wss://test.deribit.com/ws/api/v2') as websocket:
#         await websocket.send(msg)
#         while websocket.open:
#             response = await websocket.recv()
#             # print(response)

# asyncio.get_event_loop().run_until_complete(call_api(json.dumps(msg)))

import asyncio
import websockets
import json

msg = \
{
  "jsonrpc" : "2.0",
  "id" : 9929,
  "method" : "public/auth",
  "params" : {
    "grant_type" : "client_credentials",
    "client_id" : clientId,
    "client_secret" : clientSecret
  }
}

async def call_api(msg):
   async with websockets.connect('wss://test.deribit.com/ws/api/v2') as websocket:
       await websocket.send(msg)
       while websocket.open:
           response = await websocket.recv()
           # do something with the response...
           print(response)

asyncio.get_event_loop().run_until_complete(call_api(json.dumps(msg)))