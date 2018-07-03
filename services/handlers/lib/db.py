import os
import time

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
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
        for _ in range(3):
            try:
                table.scan()
                break
            except Exception as e:
                print('Failed to scan the table, sleeping 1s')
                time.sleep(1)
        else:
            raise Exception(f'Failed to get local db connection. {e}')

    else:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    return table
