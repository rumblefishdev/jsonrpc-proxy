import logging
import os
import textwrap
from os import path, sys
from urllib.parse import urlparse

import boto3

if True:
    sys.path.append(path.dirname(path.abspath(__file__)))
    from lib.db import get_table

logger = logging.getLogger(__name__)
PASSTHROUGH_ATTRIBUTES = [
    'family',
    'taskRoleArn',
    'executionRoleArn',
    'networkMode',
    'containerDefinitions',
    'volumes',
    'placementConstraints',
    'requiresCompatibilities',
    'cpu',
    'memory'
]


def update_service(event, context):
    logging.basicConfig(level=logging.INFO)
    s3_event = event['Records'][0]['s3']
    bucket_name = s3_event['bucket']['name']
    key = s3_event['object']['key']
    full_path = f's3://{bucket_name}/{key}'
    task_definition_family = os.environ['TASK_DEFINITION_FAMILY']
    cluster_arn = os.environ['CLUSTER_ARN']
    service_arn = os.environ['CF_Service']

    logger.info(f'Handling event of upload of config {full_path}')

    ecs = boto3.client('ecs')
    logger.info('Getting old task definition')
    task_definition = ecs.describe_task_definition(
        taskDefinition=task_definition_family,
    )['taskDefinition']
    old_arn = task_definition.pop('taskDefinitionArn')

    logger.info('Last ARN is {old_task_definition_arn}')

    new_env = [{'name': 'S3_CONFIG_PATH', 'value': full_path}]
    task_definition['containerDefinitions'][0]['environment'] = new_env
    new_task_definition = {
        key: task_definition[key]
        for key in PASSTHROUGH_ATTRIBUTES
        if key in task_definition
    }
    response = ecs.register_task_definition(**new_task_definition)
    new_arn = response['taskDefinition']['taskDefinitionArn']
    logger.info(f'Registered new task definition, arn: {new_arn}')

    ecs.update_service(
        cluster=cluster_arn,
        service=service_arn,
        taskDefinition=new_arn
    )
    logger.info('Called update service with new ARN')

    logger.info('Cleaning up old task definitions')
    arns = ecs.list_task_definitions(familyPrefix=task_definition_family)[
        'taskDefinitionArns']
    for arn in arns:
        if arn in (old_arn, new_arn):
            logger.info(f'Skipping task definition arn: {arn}')
            continue
        logger.info(f'Deleting task definition arn: {arn}')
        ecs.deregister_task_definition(
            taskDefinition=arn
        )


def upload_service_config(event, context):
    backends = get_table().scan()['Items']
    file_name = f'{context.aws_request_id}_nginx.conf'
    body = generate_nginx_config(backends)

    response = boto3.client('s3').put_object(
        Bucket=os.environ['NGINX_CONFIG_BUCKET_NAME'],
        Body=bytes(body, 'utf8'),
        Key=file_name,
    )


def generate_nginx_config(backends):
    leaders = []
    nodes = []
    for backend in backends:
        if not backend['is_healthy']:
            continue
        if backend['is_leader']:
            leaders.append(backend)
        else:
            nodes.append(backend)

    if not nodes:
        if not leaders:
            # nothing is up, just return something which will not fail
            return empty_config()
        else:
            return single_host_config(leaders[0]['url'])
    if len(nodes) == 1:
        return single_host_config(nodes[0]['url'])
    else:
        return load_balancing_config([node['url'] for node in nodes])


def empty_config():
    return textwrap.dedent(
        f'''
        server {{
          listen 80;
          location / {{
            return 404;
          }}
        }}
        '''
    )


def single_host_config(url):
    return textwrap.dedent(
        f'''
        server {{
          listen 80;
          location / {{
            proxy_pass {url};
          }}
        }}
        '''
    )


def load_balancing_config(urls):
    servers = '\n          '.join(f'server {urlparse(url).netloc};' for url in urls)
    return textwrap.dedent(
        f'''
        upstream service {{
          {servers}
        }}

        server {{
          listen 80;

          location / {{
            proxy_pass http://service;
            proxy_redirect off;
            proxy_next_upstream error timeout;
          }}
        }}
        '''
    )
