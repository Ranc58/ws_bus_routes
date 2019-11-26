import json
import random

import trio
from trio_websocket import open_websocket_url

from load_routes import load_routes


async def run_bus(send_channel, bus_id, route):

    start_offset = random.randint(1, len(route['coordinates']))
    first_run = True
    while True:
        route_coords = route['coordinates']
        if first_run:
            route_coords = route['coordinates'][start_offset:]
        for coords in route_coords:
            lat = coords[0]
            lng = coords[1]
            data_for_send = json.dumps({
                "busId": bus_id,
                "lat": lat,
                "lng": lng,
                "route": route['name']
            }, ensure_ascii=False)
            await send_channel.send(data_for_send)
            await trio.sleep(0.1)
        first_run = False


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def send_updates(server_address, receive_channel):
    async with open_websocket_url(server_address) as ws:
        async with receive_channel:
            async for value in receive_channel:
                print(value)
                await ws.send_message(value)
                await trio.sleep(0.1)


async def main():
    routes_counter = 0
    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(0)
        async with send_channel, receive_channel:
            nursery.start_soon(send_updates,  'ws://127.0.0.1:8080', receive_channel.clone())
            for route in load_routes():
                if routes_counter < 6:
                    random_bus_index = random.randint(99, 9999)
                    random_bus_id = generate_bus_id(route['name'], random_bus_index)
                    nursery.start_soon(run_bus, send_channel.clone(), random_bus_id, route)
                    routes_counter +=1


try:
    trio.run(main)
except KeyboardInterrupt:
    pass
