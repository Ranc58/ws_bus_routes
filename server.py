import json
import logging
from contextlib import suppress

import trio
from trio import WouldBlock
from trio_websocket import serve_websocket, ConnectionClosed

buses = {}


async def talk_to_browser(request):
    global buses
    ws = await request.accept()
    send_channel, receive_channel = trio.open_memory_channel(0)
    async with send_channel, receive_channel:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(send_browser,  ws, receive_channel.clone())
            nursery.start_soon(listen_browser, ws, send_channel.clone())


async def listen_browser(ws, send_channel):
    async with send_channel:
        while True:
            try:
                message = await ws.get_message()
            except ConnectionClosed:
                break
            else:
                await send_channel.send(message)
            logging.info(message)


def is_inside(bounds, lat, lng):
    if not bounds:
        return
    bounds = json.loads(bounds)
    coords = bounds.get('data')
    south_lat = coords.get('south_lat')
    north_lat = coords.get('north_lat')
    west_lng = coords.get('west_lng')
    east_lng = coords.get('east_lng')
    return south_lat <= lat <= north_lat and west_lng <= lng <= east_lng


async def send_browser(ws, receive_channel):
    async with receive_channel:
        screen_coords = None
        while True:
            try:
                screen_coords_msg = receive_channel.receive_nowait()
            except WouldBlock:
                pass
            else:
                screen_coords = screen_coords_msg

            data = json.dumps({
                "msgType": "Buses",
                "buses": [{
                    "busId": bus['busId'],
                    "lat": bus['lat'],
                    "lng": bus['lng'],
                    "route": bus['route']
                } for _, bus in buses.items() if is_inside(screen_coords, bus['lat'], bus['lng'])
                ]}, ensure_ascii=False)
            try:
                await ws.send_message(data)
            except ConnectionClosed:
                break
            await trio.sleep(0.1)


async def gates_listener(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            dict_msg = json.loads(message)
            logging.info(dict_msg)
            buses.update({dict_msg.get('busId'): dict_msg})
        except ConnectionClosed:
            break


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, gates_listener, '127.0.0.1', 8080, None)
        nursery.start_soon(serve_websocket, talk_to_browser, '127.0.0.1', 8000, None)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        logging.basicConfig(level=logging.INFO)
        trio.run(main)
