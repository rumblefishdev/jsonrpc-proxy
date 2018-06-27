from datetime import datetime
from os import path, sys

from schema import Schema, SchemaError

if True:
    sys.path.append(path.dirname(path.abspath(__file__)))
    from lib.db import get_table
    from lib import json


add_backend_schema_request = Schema({
    'url': str,
    'is_leader': bool
})


def error_response(code, error, error_type='error'):
    return {
        'statusCode': code,
        'body': json.dumps({
            'type': error_type,
            'error': str(error),
            'errorClass': str(type(error))
        })
    }


def add_backend(event, context):
    try:
        params = add_backend_schema_request.validate(json.loads(event['body']))
    except json.JSONDecodeError as e:
        return error_response(400, e, error_type='parse_error')
    except SchemaError as e:
        return error_response(400, e, error_type='validation_error')

    params.update({
        'is_healthy': False,
        'when_added': datetime.utcnow().isoformat()
    })
    table = get_table()
    try:
        response = table.put_item(Item=params)
    except Exception as e:
        return error_response(500, e)
    return {
        'statusCode': 201,
        'body': json.dumps(params)
    }


def list_backends(event, context):
    table = get_table()
    items = table.scan()
    return {
        'statusCode': 200,
        'body': json.dumps(items['Items'])
    }
