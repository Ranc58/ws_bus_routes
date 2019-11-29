import json
import logging
from contextlib import suppress

import trio
from trio_websocket import serve_websocket, ConnectionClosed

buses = {}


async def gates_listener(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            dict_msg = json.loads(message)
            logging.info(dict_msg)
            buses.update({
                dict_msg.get('busId'): dict_msg
            })
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    global buses
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_browser,  ws)
        nursery.start_soon(listen_browser, ws)


async def listen_browser(ws):
    while True:
        try:
            message = await ws.get_message()
        except ConnectionClosed:
            break
        logging.info(message)


async def send_browser(ws):
    while True:
        data = json.dumps({
            "msgType": "Buses",
            "buses": [{"busId": bus['busId'], "lat": bus['lat'], "lng": bus['lng'], "route": bus['route']} for _, bus in buses.items()]
        }, ensure_ascii=False)
        try:
            await ws.send_message(data)
        except ConnectionClosed:
            break
        await trio.sleep(0.1)


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, gates_listener, '127.0.0.1', 8080, None)
        nursery.start_soon(serve_websocket, talk_to_browser, '127.0.0.1', 8000, None)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        logging.basicConfig(level=logging.INFO)
        trio.run(main)
