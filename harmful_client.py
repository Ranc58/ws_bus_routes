import json
import logging
import random
from contextlib import suppress


import asyncclick as click
import trio
from trio_websocket import open_websocket_url, ConnectionClosed

ERROR_MESSAGES = [
    'error json',
    json.dumps({'msgType': 'ErrorMsgType'})
]

@click.command()
@click.option("--log", '-l', is_flag=True, default=False, help="Enable logging", show_default=True)
@click.option("--host", '-h', default='127.0.0.1', help="Destination host", show_default=True)
@click.option("--port", '-p', default='8000', help="Destination port", show_default=True)
async def main(log, host, port):
    if not log:
        logger = logging.getLogger()
        logger.disabled = True
    url = f'ws://{host}:{port}'
    async with open_websocket_url(url) as ws:
        while True:
            try:
                error_message = random.choice(ERROR_MESSAGES)
                await ws.send_message(error_message)
                logging.info(f'Sent message "{error_message}" to {url}')
                message = await ws.get_message()
                logging.info(f'Received message: {message}')
            except (OSError, ConnectionClosed) as e:
                logging.error(f'Connection failed: {e}')
            await trio.sleep(1)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        logging.basicConfig(level=logging.INFO)
        main(_anyio_backend="trio")
