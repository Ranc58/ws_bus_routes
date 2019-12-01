import json
import logging
from contextlib import suppress
from dataclasses import dataclass

import trio
import asyncclick as click
from trio_websocket import serve_websocket, ConnectionClosed

buses = {}


@dataclass
class Bus:
    busId: int
    lat: float
    lng: float
    route: str


@dataclass
class WindowBounds:
    south_lat: float = 0
    north_lat: float = 0
    west_lng: float = 0
    east_lng: float = 0

    def is_inside(self, lat, lng):
        south_lat = self.south_lat
        north_lat = self.north_lat
        west_lng = self.west_lng
        east_lng = self.east_lng
        return south_lat <= lat <= north_lat and west_lng <= lng <= east_lng

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng


def is_inside(bounds, lat, lng):
    if not bounds:
        return
    south_lat = bounds.south_lat
    north_lat = bounds.north_lat
    west_lng = bounds.west_lng
    east_lng = bounds.east_lng
    return south_lat <= lat <= north_lat and west_lng <= lng <= east_lng


async def send_buses(ws, bounds):
    buses_data = {
        "msgType": "Buses",
        "buses": [{
            "busId": bus.busId,
            "lat": bus.lat,
            "lng": bus.lng,
            "route": bus.route
        } for _, bus in buses.items() if bounds.is_inside(bus.lat, bus.lng)
        ]}
    data = json.dumps(buses_data, ensure_ascii=False)
    logging.info(f"{len(buses_data['buses'])} buses inside bounds")
    await ws.send_message(data)


async def listen_browser(ws, bounds):
    while True:
        try:
            msg = await ws.get_message()
        except ConnectionClosed:
            break
        logging.info(msg)
        msg_data = json.loads(msg)
        coords_data = msg_data.get('data')
        bounds.update(**coords_data)


async def talk_to_browser(ws, bounds):
    global buses
    while True:
        try:
            await send_buses(ws, bounds)
        except ConnectionClosed:
            break
        await trio.sleep(0.1)


async def browser_proccess(request):
    ws = await request.accept()
    bounds = WindowBounds()
    # Here we use mutable arg "bounds" (changes in function "listen_browser")
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
        nursery.start_soon(talk_to_browser, ws, bounds)


async def gates_listener(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            dict_msg = json.loads(message)
            bus = Bus(**dict_msg)
            logging.info(dict_msg)
            buses.update({bus.busId: bus})
        except ConnectionClosed:
            break


@click.command()
@click.option("--imitator_host", '-ih', default='127.0.0.1', help="Bus imitator host", show_default=True)
@click.option("--imitator_port", '-ip', default=8080, help="Bus imitator port", show_default=True)
@click.option("--browser_port", '-bp', default=8000, help="Browser port", show_default=True)
@click.option("--log", '-l', is_flag=True, default=False, help="Enable logging", show_default=True)
async def main(imitator_host, imitator_port, browser_port, log):
    if not log:
        logger = logging.getLogger()
        logger.disabled = True
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, gates_listener, imitator_host, imitator_port, None)
        nursery.start_soon(serve_websocket, browser_proccess, '127.0.0.1', browser_port, None)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        logging.basicConfig(level=logging.INFO)
        main(_anyio_backend="trio")
