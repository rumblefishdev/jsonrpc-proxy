import textwrap

import pytest
from handlers.service import (empty_config, generate_nginx_config,
                              load_balancing_config, single_host_config)


def test_single_host():
    url = 'https://infura.com/aaa'
    config = single_host_config(url)
    expected = textwrap.dedent(
        '''
        server {
          listen 80;
          location / {
            proxy_pass https://infura.com/aaa;
          }
        }
        '''
    )
    assert config == expected


def test_load_balancing():
    urls = ['http://my-host1.com:200', 'http://my-host2.com']
    config = load_balancing_config(urls)
    expected = textwrap.dedent(
        '''
        upstream service {
          server my-host1.com:200;
          server my-host2.com;
        }

        server {
          listen 80;

          location / {
            proxy_pass http://service;
            proxy_redirect off;
            proxy_next_upstream error timeout;
          }
        }
        '''
    )
    assert config == expected


urls = [f'http://url{i}' for i in range(4)]


def backend(url, healthy, is_leader): return {
    'url': url,
    'is_healthy': healthy,
    'is_leader': is_leader
}


@pytest.mark.parametrize('backends,expected', [
    (
        # single node selected
        [
            backend(urls[0], False, False),
            backend(urls[1], True, False),
            backend(urls[2], True, True)
        ],
        single_host_config(urls[1])
    ),
    (
        # multiple nodes selected
        [
            backend(urls[0], False, False),
            backend(urls[1], True, False),
            backend(urls[2], True, False),
            backend(urls[3], True, True)
        ],
        load_balancing_config([urls[1], urls[2]])
    ),
    (
        # fallback to leader
        [
            backend(urls[0], False, False),
            backend(urls[1], False, False),
            backend(urls[2], False, False),
            backend(urls[3], True, True)
        ],
        single_host_config(urls[3])
    ),
    (
        # everything dead
        [
            backend(urls[0], False, False),
            backend(urls[1], False, False),
            backend(urls[2], False, False),
            backend(urls[3], False, True)
        ],
        empty_config()
    ),

])
def test_generate_config(backends, expected):
    assert generate_nginx_config(backends) == expected
