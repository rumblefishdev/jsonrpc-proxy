import json
import os
from datetime import datetime

import boto3
from schema import Schema, SchemaError

dynamodb = boto3.client('dynamodb')
db_name = os.environ['DYNAMODB_TABLE']


add_backend_schema_request = Schema({
    'url': str,
    'is_leader': bool
})


def error_response(code, error, error_type='error'):
    return {
        'statusCode': code,
        'body': json.dumps({
            'type': error_type,
            'error': str(error)
        })
    }


def add_backend(event, context):
    try:
        params = validate_schema()
    except SchemaError as e:
        return error_response(400, e, error_type='validation_error')

    params.update({
        'is_healthy': False,
        'when_added': datetime.utcnow().isoformat()
    })
    try:
        response = dynamodb.put_item({
            'TableName': db_name,
            'Item'=params
        })
    except Exception as e:
        return error_response(500, e)
    return {
        'statusCode': 201,
        'body': json.dumps(params)
    }
