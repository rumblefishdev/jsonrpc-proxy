import pytest


@pytest.fixture(autouse=True)
def environ(monkeypatch):
    monkeypatch.setenv('DYNAMODB_TABLE', 'jsonrpc-proxy-dev')
    monkeypatch.setenv('CLOUDWATCH_NAMESPACE',  'test')
    monkeypatch.setenv('STACK_NAME',  'jsonrpc-proxy-dev')
