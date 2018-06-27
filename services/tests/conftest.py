import pytest


@pytest.fixture(autouse=True)
def environ(monkeypatch):
    monkeypatch.setenv('DYNAMODB_TABLE', 'jsonrpc-proxy-dev')
    monkeypatch.setenv('DYNAMODB_LOCAL_ENDPOINT',  'http://localhost:8000')
