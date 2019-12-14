import json
import logging
from contextlib import suppress
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import List

import trio
import asyncclick as click
from trio_websocket import serve_websocket, ConnectionClosed

from serializers import BusSchema, WindowBoundSchema

buses = {}
logger = logging.getLogger('app_logger')


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
    errors: List = field(default_factory=list)

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

    def add_errors(self, errors):
        self.errors = errors


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
    logger.debug(f"{len(buses_data['buses'])} buses inside bounds")
    data = json.dumps(buses_data, ensure_ascii=False)
    await ws.send_message(data)


def check_browser_message(msg_data):
    return WindowBoundSchema().validate(data=msg_data)


def check_gates_message(msg_data):
    return BusSchema().validate(data=msg_data)


def check_message(message, source_type):
    result = {'errors': None, "data": message}
    try:
        msg_data = json.loads(message)
    except JSONDecodeError:
        result['errors'] = ['Requires valid JSON']
        return result
    else:
        result['data'] = msg_data.get('data', msg_data)

    check_funcs = {
        'browser': check_browser_message,
        'bus': check_gates_message,
    }
    func_for_check = check_funcs.get(source_type)
    if not func_for_check:
        result['errors'] = ['Unknown data source']
    else:
        result['errors'] = func_for_check(msg_data)
    return result


async def listen_browser(ws, bounds):
    while True:
        try:
            msg = await ws.get_message()
        except ConnectionClosed:
            break
        logger.debug(msg)
        msg_data = check_message(msg, 'browser')
        errors = msg_data.get('errors')
        if errors:
            bounds.add_errors(errors)
            buses_data = {
                "msgType": "errors",
                "errors": errors
            }

            data = json.dumps(buses_data, ensure_ascii=False)
            await ws.send_message(data)
        else:
            coords_data = msg_data.get('data')
            bounds.update(**coords_data)


async def talk_to_browser(ws, bounds):
    global buses
    while True:
        try:
            if not bounds.errors:
                await send_buses(ws, bounds)
        except ConnectionClosed:
            break
        await trio.sleep(0.1)


async def process_to_browser(request):
    ws = await request.accept()
    bounds = WindowBounds()
    # Here we use mutable arg "bounds" (changes in function "listen_browser")
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
        nursery.start_soon(talk_to_browser, ws, bounds)


async def listen_gates(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            msg_data = check_message(message, 'bus')
            errors = msg_data.get('errors')
            if errors:
                error_message = json.dumps({
                    "msgType": "errors",
                    "errors": errors
                })
                await ws.send_message(error_message)
            else:
                dict_msg = msg_data.get('data')
                bus = Bus(**dict_msg)
                logger.debug(dict_msg)
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
        logger.disabled = True
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, listen_gates, imitator_host, imitator_port, None)
        nursery.start_soon(serve_websocket, process_to_browser, '127.0.0.1', browser_port, None)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        main(_anyio_backend="trio")
