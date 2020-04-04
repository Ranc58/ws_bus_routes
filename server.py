import asyncio
import contextlib
import json
import logging
from contextlib import suppress, asynccontextmanager
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import List

import aioamqp
import trio
import asyncclick as click
import trio_asyncio
from trio_asyncio import aio_as_trio
from trio_websocket import serve_websocket, ConnectionClosed

from fake_bus import relaunch_on_disconnect
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


@asynccontextmanager
async def rabbit_connection(rabbit_user, rabbit_pass, rabbit_host, rabbit_port):
    transport, protocol = None, None
    try:
        transport, protocol = await aioamqp.connect(
            login_method="PLAIN",
            login=rabbit_user,
            password=rabbit_pass,
            host=rabbit_host,
            port=rabbit_port,
        )
        channel = await protocol.channel()
        await channel.exchange(exchange_name='buses', type_name='direct')
        result = await channel.queue(queue_name='', exclusive=True, durable=False)
        queue_name = result['queue']
        yield queue_name, channel
    finally:
        if protocol:
            await protocol.close()
        if transport:
            transport.close()


async def callback(channel, body, envelope, properties):
    msg_data = check_message(body, 'bus')
    if not msg_data.get('errors'):
        dict_msg = msg_data.get('data')
        bus = Bus(**dict_msg)
        logger.debug(dict_msg)
        buses.update({bus.busId: bus})


@aio_as_trio
@relaunch_on_disconnect
async def listen_rabbit(rabbit_user, rabbit_pass, rabbit_host, rabbit_port):
    async with rabbit_connection(rabbit_user, rabbit_pass, rabbit_host, rabbit_port) as (queue_name, channel):
        await channel.queue_bind(
            exchange_name='buses',
            queue_name=queue_name,
            routing_key='',
        )
        while True:
            await channel.basic_consume(callback, queue_name=queue_name, no_ack=True)
            await asyncio.sleep(1)


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


@click.command()
@click.option("--browser_port", '-bp', default=8000, help="Browser port", show_default=True)
@click.option("--log", '-l', is_flag=True, default=False, help="Enable logging", show_default=True)
@click.option("--rabbit_user", '-ru', default="rabbitmq", help="Login for RabbitMQ", show_default=True)
@click.option("--rabbit_pass", '-rpass', default="rabbitmq", help="Password for RabbitMQ", show_default=True)
@click.option("--rabbit_host", '-rh', default="127.0.0.1", help="RabbitMQ host", show_default=True)
@click.option("--rabbit_port", '-rp', default=5672, help="RabbitMQ port", show_default=True)
async def main(browser_port, log, rabbit_user, rabbit_pass, rabbit_host, rabbit_port):
    if not log:
        logger.disabled = True
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(trio_asyncio.open_loop())
        nursery = await stack.enter_async_context(trio.open_nursery())
        nursery.start_soon(listen_rabbit, rabbit_user, rabbit_pass, rabbit_host, rabbit_port)
        nursery.start_soon(serve_websocket, process_to_browser, '127.0.0.1', browser_port, None)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        main(_anyio_backend="trio")
