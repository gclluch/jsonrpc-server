# JSON-RPC Server for Python

A lightweight, easy-to-use JSON-RPC 2.0 server implementation in Python, designed for simplicity and minimal dependencies. This package allows you to quickly set up a JSON-RPC server to handle remote procedure calls in a standardized way, supporting both single and batch requests.

## Features

- Simple and straightforward JSON-RPC 2.0 compliance.
- Supports method registration for handling RPC calls.
- Handles single and batch requests.
- Built-in support for notifications (requests without response).
- Easy integration into existing Python applications.

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