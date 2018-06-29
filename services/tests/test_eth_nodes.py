import asyncio
from unittest import mock

import pytest
from aioresponses import aioresponses
from handlers.eth_nodes import get_block_numbers
from handlers.lib.db import get_table

url1 = 'http://url1'
url2 = 'http://url2'


@pytest.fixture(autouse=True)
def mock_cloudwatch():
    with mock.patch('boto3.client') as m:
        yield m


@pytest.fixture
def mock_trigger_service():
    with mock.patch('handlers.eth_nodes.trigger_service_update') as m:
        yield m


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
        'elapsed': 100,
        'was_healthy': previous_block_number is not None
    }


def clear_all_items():
    table = get_table()
    items = table.scan()['Items']
    for item in items:
        table.delete_item(Key={'url': item['url']})


def test_get_block_numbers_timeout(mock_trigger_service):
    clear_all_items()
    set_state(url1, block_number=10, leader=True)
    set_state(url2, block_number=5, leader=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(15)})
        responses.post(url2, exception=asyncio.TimeoutError())

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=15)
    expect(url2, healthy=False, block_number=5)

    assert mock_trigger_service.called


def test_get_block_numbers_recover(mock_trigger_service):
    clear_all_items()
    set_state(url1, block_number=10, leader=True)
    set_state(url2, block_number=5, leader=False, is_healthy=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(15)})
        responses.post(url2, payload={'result': hex(15)})

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=15)
    expect(url2, healthy=True, block_number=15)

    assert mock_trigger_service.called


def test_get_block_numbers_delayed_nonhealthy(mock_trigger_service):
    clear_all_items()
    set_state(url1, block_number=25, leader=True)
    set_state(url2, block_number=10, leader=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(25)})
        responses.post(url2, payload={'result': hex(10)})

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=25)
    expect(url2, healthy=False, block_number=10)

    assert mock_trigger_service.called


def test_get_block_numbers_no_leader(mock_trigger_service):
    clear_all_items()
    set_state(url1, block_number=25, leader=False)
    set_state(url2, block_number=10, leader=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(25)})
        responses.post(url2, payload={'result': hex(10)})

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=25)
    expect(url2, healthy=False, block_number=10)

    assert mock_trigger_service.called


def test_get_block_doesnt_update_when_no_need(mock_trigger_service, mock_cloudwatch):
    clear_all_items()
    set_state(url1, block_number=25, leader=False)
    set_state(url2, block_number=25, leader=False)
    with aioresponses() as responses:
        responses.post(url1, payload={'result': hex(25)})
        responses.post(url2, payload={'result': hex(25)})

        get_block_numbers(event={}, context={})

    expect(url1, healthy=True, block_number=25)
    expect(url2, healthy=True, block_number=25)

    assert not mock_trigger_service.called

    assert mock_cloudwatch.return_value.put_metric_data.called
    assert mock_cloudwatch.return_value.put_metric_data.call_args == mock.call(
        MetricData=[
            {
                'MetricName': 'ETH node block number',
                'Timestamp': mock.ANY,
                'Value': 25,
                'Unit': 'None',
                'StorageResolution': 60,
                'Dimensions': [{'Name': 'Node URL', 'Value': 'http://url2'}]
            },
            {
                'MetricName': 'ETH node block number',
                'Timestamp': mock.ANY,
                'Value': 25,
                'Unit': 'None',
                'StorageResolution': 60,
                'Dimensions': [{'Name': 'Node URL', 'Value': 'http://url1'}]
            },
            {
                'MetricName': 'eth_getBlockNumber response time',
                'Timestamp': mock.ANY,
                'Value': mock.ANY,
                'Unit': 'Microseconds',
                'StorageResolution': 60,
                'Dimensions': [{'Name': 'Node URL', 'Value': 'http://url2'}]
            },
            {
                'MetricName': 'eth_getBlockNumber response time',
                'Timestamp': mock.ANY,
                'Value': mock.ANY,
                'Unit': 'Microseconds',
                'StorageResolution': 60,
                'Dimensions': [{'Name': 'Node URL', 'Value': 'http://url1'}]
            },
            {
                'MetricName': 'Number of healthy ETH nodes',
                'Timestamp': mock.ANY,
                'Value': 2,
                'Unit': 'None',
                'StorageResolution': 60,
                'Dimensions': [{'Name': 'Stack name', 'Value': 'jsonrpc-proxy-dev'}]
            },
            {
                'MetricName': 'ETH node block difference',
                'Timestamp': mock.ANY,
                'Value': 0,
                'Unit': 'None',
                'StorageResolution': 60,
                'Dimensions': [{'Name': 'Node URL', 'Value': 'http://url2'}]
            },
            {
                'MetricName': 'ETH node block difference',
                'Timestamp': mock.ANY,
                'Value': 0,
                'Unit': 'None',
                'StorageResolution': 60,
                'Dimensions': [{'Name': 'Node URL', 'Value': 'http://url1'}]
            }
        ], Namespace='test')
