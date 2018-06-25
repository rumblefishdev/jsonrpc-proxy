import asyncio
from unittest import mock

import pytest
from aioresponses import aioresponses
from handlers.eth_nodes import get_block_numbers
from handlers.lib.db import get_table

url1 = 'http://url1'
url2 = 'http://url2'


def set_state(url, block_number, leader=False, is_healthy=True):
    get_table().put_item(
        Item={
            'url': url,
            'block_number': block_number,
            'is_healthy': is_healthy,
            'is_leader': leader,
        }
    )


def expect(url, healthy, block_number):
    item = get_table().get_item(Key={'url': url})
    assert item['Item']['is_healthy'] is healthy, item['Item']
    assert item['Item']['block_number'] == block_number, item['Item']


def times_for(url, block_number, is_leader=False, previous_block_number=None):
    return {
        'url': url,
        'previous_block_number': previous_block_number or block_number,
        'block_number': block_number,
        'is_leader': is_leader,
        'elapsed': 0.1,
        'was_healthy': previous_block_number is not None
    }


def clear_all_items():
    table = get_table()
    items = table.scan()['Items']
    for item in items:
        table.delete_item(Key={'url': item['url']})


def test_get_block_numbers_timeout():
    clear_all_items()
    set_state(url1, block_number=10, leader=True)
    set_state(url2, block_number=5, leader=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(15)})
        responses.post(url2, exception=asyncio.TimeoutError())

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=15)
    expect(url2, healthy=False, block_number=5)


def test_get_block_numbers_recover():
    clear_all_items()
    set_state(url1, block_number=10, leader=True)
    set_state(url2, block_number=5, leader=False, is_healthy=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(15)})
        responses.post(url2, payload={'result': hex(15)})

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=15)
    expect(url2, healthy=True, block_number=15)


def test_get_block_numbers_delayed_nonhealthy():
    clear_all_items()
    set_state(url1, block_number=25, leader=True)
    set_state(url2, block_number=10, leader=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(25)})
        responses.post(url2, payload={'result': hex(10)})

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=25)
    expect(url2, healthy=False, block_number=10)


def test_get_block_numbers_no_leader():
    clear_all_items()
    set_state(url1, block_number=25, leader=False)
    set_state(url2, block_number=10, leader=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(25)})
        responses.post(url2, payload={'result': hex(10)})

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=25)
    expect(url2, healthy=False, block_number=10)
