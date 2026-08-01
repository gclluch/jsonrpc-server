"""Cases drawn from the JSON-RPC 2.0 spec that earlier versions got wrong."""

import requests

SERVER_URL = "http://localhost:8000"


def post(payload):
    return requests.post(SERVER_URL, json=payload)


def test_invalid_method_type_without_id_is_an_error_not_a_notification():
    # Spec worked example: {"jsonrpc": "2.0", "method": 1, "params": "bar"}
    # -> -32600 with a null id. It has no 'id', but a malformed object is not
    # a notification.
    r = post({"jsonrpc": "2.0", "method": 1, "params": "bar"})
    assert r.status_code == 200, f"got {r.status_code} with body {r.text!r}"
    body = r.json()
    assert body["error"]["code"] == -32600
    assert body["id"] is None


def test_malformed_id_is_not_echoed_back():
    # An id of a disallowed type must never be reflected: the response would
    # not be valid JSON-RPC. It is nulled out.
    r = post({"jsonrpc": "2.0", "method": "ping", "id": {"a": 1}})
    body = r.json()
    assert body["error"]["code"] == -32600
    assert body["id"] is None, f"malformed id echoed back: {body['id']!r}"


def test_bad_version_with_malformed_id_still_nulls_the_id():
    r = post({"jsonrpc": "1.0", "method": "ping", "id": ["not", "valid"]})
    body = r.json()
    assert body["error"]["code"] == -32600
    assert body["id"] is None


def test_server_defined_error_keeps_the_request_id():
    r = post({"jsonrpc": "2.0", "method": "app_error", "id": 42})
    body = r.json()
    assert body["error"]["code"] == -32001
    assert body["id"] == 42, "server-defined error dropped the request id"


def test_exception_is_importable_from_the_package_root():
    from jsonrpc_server import JSONRPCException

    assert JSONRPCException(-32001, "x", 7).id == 7
