# JSON-RPC Server for Python

A JSON-RPC 2.0 server in **~200 lines of pure standard library** — no dependencies, at install time or at runtime. `pip install jsonrpc-server-py` pulls in nothing else, and CI asserts that on every push.

That is the whole pitch. If you want middleware, async, or an ecosystem, use [`jsonrpcserver`](https://pypi.org/project/jsonrpcserver/). If you want a spec-compliant endpoint you can read start to finish and vendor into a project that cannot take on dependencies, use this.

## Features

- **Zero dependencies** — stdlib `http.server` and `json`, nothing more.
- Spec-compliant error codes: `-32700` parse, `-32600` invalid request, `-32601` method not found, `-32602` invalid params, `-32603` internal error.
- Single requests, batches, and notifications (including all-notification batches, which correctly return no body).
- Threaded by default (`ThreadingHTTPServer`), so one slow method does not block every other client.
- Errors travel in the JSON body with HTTP 200, as the spec intends — the transport succeeded even when the call did not.

Refer here for details: https://www.jsonrpc.org/specification

## Installation

To install the JSON-RPC Server, simply use pip:

```bash
pip install jsonrpc-server-py
```

## Quick Start

Define the methods you want to expose through JSON-RPC, register your methods with the server, and run the server


```python
from jsonrpc_server import register_method, run

def add(a, b):
    return a + b

register_method('add', add)

if __name__ == "__main__":
    run(address='localhost', port=8000)
```


## Example

Request:

```bash
{
  "jsonrpc": "2.0",
  "method": "add",
  "params": [1, 2],
  "id": 1
}
```

Result:

```bash
{
  "jsonrpc": "2.0",
  "result": 3,
  "id": 1
}
```

## Batch Requests

Send a JSON array to process multiple calls in one HTTP request. Each call gets a matching response, in order:

```bash
[
  {"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": 1},
  {"jsonrpc": "2.0", "method": "add", "params": [3, 4], "id": 2}
]
```

Result:

```bash
[
  {"jsonrpc": "2.0", "result": 3, "id": 1},
  {"jsonrpc": "2.0", "result": 7, "id": 2}
]
```

## Notifications

Omit `id` to send a notification: the method still runs, but no response is sent (HTTP 204 No Content). Use this for fire-and-forget calls where you don't need the result:

```bash
{"jsonrpc": "2.0", "method": "add", "params": [1, 2]}
```

A batch made up entirely of notifications also gets no response body.

## Limitations

This project favors a small, readable, stdlib-only implementation over feature completeness:

- No HTTPS - put a reverse proxy (nginx, Caddy) in front if you need TLS.
- No authentication or authorization - add your own layer if the server is exposed beyond a trusted network.
- Threaded, not async - each request runs in its own thread (`ThreadingHTTPServer`), which is enough to avoid one slow call blocking others, but it isn't an async event loop and won't scale to very high concurrency.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to improve the project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.