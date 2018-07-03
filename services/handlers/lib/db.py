import os

import boto3


def get_table():
    local_endpoint = os.environ.get('DYNAMODB_LOCAL_ENDPOINT')
    if local_endpoint:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=local_endpoint,
            region_name='us-east-1',
            aws_access_key_id='anything',
            aws_secret_access_key='anything',
        )
    else:
        dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table(os.environ['DYNAMODB_TABLE'])
