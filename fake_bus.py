import json
import logging
import random
from contextlib import suppress

import trio
import asyncclick as click
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


def generate_bus_id(route_id, bus_index, emulator_id):
    uniq_bus_id = f"{route_id}-{bus_index}"
    if emulator_id:
        uniq_bus_id = f'{emulator_id}-{uniq_bus_id}'
    return uniq_bus_id


async def send_updates(server_address, receive_channel, refresh_timeout):
    async with open_websocket_url(server_address) as ws:
        async with receive_channel:
            async for value in receive_channel:
                await ws.send_message(value)
                await trio.sleep(refresh_timeout)


async def get_channels(nursery, sockets_count, refresh_timeout, host, port):
    send_channels = []
    for _ in range(sockets_count):
        send_channel, receive_channel = trio.open_memory_channel(0)
        async with send_channel, receive_channel:
            nursery.start_soon(send_updates, f'ws://{host}:{port}', receive_channel.clone(), refresh_timeout)
            send_channels.append(send_channel.clone())
    return send_channels


@click.command()
@click.option("--routes_number", '-r', default=10, help="Number of routes.", show_default=True)
@click.option("--buses_per_route", '-b', default=5, help="Number of buses per one route", show_default=True)
@click.option("--sockets_count", '-s', default=5, help="Count of websockets.", show_default=True)
@click.option("--emulator_id", '-e', default=None, help="ID for buses", show_default=True)
@click.option("--refresh_timeout", '-rt', default=0.1, help="Timeout for refresh (in secs)", show_default=True)
@click.option("--log", '-l', is_flag=True, default=False, help="Enable logging", show_default=True)
@click.option("--host", '-h', default='127.0.0.1', help="Destination host", show_default=True)
@click.option("--port", '-p', default='8080', help="Destination port", show_default=True)
async def main(routes_number, buses_per_route, sockets_count, emulator_id, refresh_timeout, log, host, port):
    if not log:
        logger = logging.getLogger()
        logger.disabled = True
    async with trio.open_nursery() as nursery:
        processed_routes = 0
        channels = await get_channels(nursery, sockets_count, refresh_timeout, host, port)
        for route in load_routes(routes_count=routes_number):
            for bus in range(buses_per_route):
                send_channel = random.choice(channels)
                random_bus_index = random.randint(99, 9999)
                random_bus_id = generate_bus_id(route['name'], random_bus_index, emulator_id)
                nursery.start_soon(run_bus, send_channel, random_bus_id, route)
                processed_routes += 1
            logging.info(f'buses send {processed_routes}')


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        logging.basicConfig(level=logging.INFO)
        main(_anyio_backend="trio")
