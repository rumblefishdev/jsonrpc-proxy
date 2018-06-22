import asyncio
import logging
from os import path, sys

import aiohttp

if True:
    sys.path.append(path.dirname(path.abspath(__file__)))
    from lib.db import get_table


logger = logging.getLogger(__name__)


def get_block_numbers(event, context):
    table = get_table()
    items = table.scan()['Items']
    loop = asyncio.get_event_loop()
    block_numbers = loop.run_until_complete(
        fetch_block_numbers(items=items)
    )

    for item in items:
        block_number = block_numbers[item['url']]
        if not block_number:
            # failed to fetch or timeout
            continue
        table.update_item(
            Key={'url': item['url']},
            UpdateExpression='SET blockNumber = :vblockNumber',
            ExpressionAttributeValues={
                ':vblockNumber': block_number
            }
        )


async def fetch_block_numbers(items):
    async with aiohttp.ClientSession() as session:
        urls = [item['url'] for item in items]
        coros = [fetch_block_number(session, url) for url in urls]
        block_numbers = await asyncio.gather(*coros)
    return dict(zip(urls, block_numbers))


timeout = aiohttp.ClientTimeout(total=2)


async def fetch_block_number(session, url):
    data = {
        'jsonrpc': '2.0',
        'method': 'eth_blockNumber',
        'params': [],
        'id': 1
    }
    try:
        async with session.post(url, json=data, timeout=timeout) as response:
            if response.status == 200:
                response_body = await response.json()
                return int(response_body['result'], 16)
            else:
                response_test = await response.text()
                logger.info(f'Got status code f{response.status} body: f{response_text}')

    except Exception as e:
        logger.exception('Failed to get blockNumber', extra={'url': url})
