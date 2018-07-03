import json
from datetime import datetime

import pytest
from handlers import backends


def from_iso(iso, fmt="%Y-%m-%dT%H:%M:%S.%f"):
    """
    Convert UTC time string to time.struct_time
    """
    # change datetime.datetime to time, return time.struct_time type
    return datetime.strptime(iso, fmt)


@pytest.fixture
def body():
    return {'url': 'http://my.rpc.local:8545', 'is_leader': False}


@pytest.fixture
def event(body):
    return {'body': json.dumps(body)}


def test_add_backend(event, body):
    response = backends.add_backend(event, context={})
    assert response['statusCode'] == 201, response

    db = backends.get_table()
    entry = db.get_item(Key={'url': body['url']})
    assert entry['Item']['is_leader'] is False
    assert type(from_iso(entry['Item']['when_added'])) is datetime
