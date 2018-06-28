import os
import textwrap
from os import path, sys
from urllib.parse import urlparse

import boto3

if True:
    sys.path.append(path.dirname(path.abspath(__file__)))
    from lib.db import get_table


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
