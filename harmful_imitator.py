import json
import logging
import random
from contextlib import suppress


import trio
import asyncclick as click
from trio_websocket import open_websocket_url, ConnectionClosed


ERROR_MESSAGES = {
    'client': [
        'error json',
        json.dumps({'msgType': 'ErrorMsgType'}),
        json.dumps({'msgType': 'newBounds', "data": {'lat': 20, 'north_lat': 30}}),
        json.dumps({"data": {'east_lng': 20, 'north_lat': 20, 'south_lat': 20, 'west_lng': 35}}),
    ],
    'bus': [
        'error json',
        json.dumps({'lat': 36.2}),
        json.dumps({'BusId': 12, "lat": "error"}),
    ],
}


@click.command()
@click.option("--log", '-l', is_flag=True, default=False, help="Enable logging", show_default=True)
@click.option("--host", '-h', default='127.0.0.1', help="Destination host", show_default=True)
@click.option("--port", '-p', default=8000, help="Destination port", show_default=True)
@click.option("--imitator_type", '-it', default='client', help="Type of imitator(client/bus)", show_default=True)
async def main(log, host, port, imitator_type):
    if not log:
        logger = logging.getLogger()
        logger.disabled = True
    url = f'ws://{host}:{port}'
    async with open_websocket_url(url) as ws:
        while True:
            try:
                error_message = random.choice(ERROR_MESSAGES.get(imitator_type))
                await ws.send_message(error_message)
                logging.info(f'Sent message "{error_message}" to {url}')
                message = await ws.get_message()
                logging.info(f'Received message: {message}')
            except (OSError, ConnectionClosed) as e:
                logging.error(f'Connection failed: {e}')
                break
            await trio.sleep(1)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        logging.basicConfig(level=logging.INFO)
        main(_anyio_backend="trio")
