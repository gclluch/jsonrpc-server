"""JSON-RPC 2.0 server implementation (stdlib only)."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


class JSONRPCException(Exception):
    """Carries a JSON-RPC error code/message/id through the call stack."""

    def __init__(self, code, message, id_=None):
        self.code = code
        self.message = message
        self.id = id_
        super().__init__(message)


class JSONRPCServer(BaseHTTPRequestHandler):
    """JSON-RPC server implementation."""

    methods = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # ponytail: give every subclass its own registry instead of sharing
        # (and silently mutating) the base class's dict.
        cls.methods = {}

    @classmethod
    def register_method(cls, name, method):
        """Register a method to be exposed by the server."""
        if name.startswith('rpc.'):
            raise ValueError("Method names starting with 'rpc.' are reserved for JSON-RPC internal methods and extensions.")
        cls.methods[name] = method

    def do_POST(self):
        """Handle POST requests."""
        try:
            post_data = self._read_body()
            json_data = self.parse_request_data(post_data)

            if isinstance(json_data, list):
                result = self.process_batch_request(json_data)
            elif isinstance(json_data, dict):
                result = self.process_single_request(json_data)
            else:
                raise JSONRPCException(-32600, "Invalid Request", None)
        except JSONRPCException as e:
            result = json.dumps(self.error_response(e.code, e.message, e.id)), 200

        if result is None:
            self.send_response(204)  # No Content: request was a notification (or all-notification batch)
            self.end_headers()
            return

        response, status_code = result
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def _read_body(self):
        """Read the request body using Content-Length."""
        try:
            content_length = int(self.headers.get('Content-Length'))
        except (TypeError, ValueError):
            raise JSONRPCException(-32600, "Invalid Request: Content-Length header is required", None)
        return self.rfile.read(content_length)

    def process_single_request(self, json_data):
        """Process a single JSON-RPC request object."""
        response = self.handle_one(json_data)
        if response is None:  # notification: no response body at all
            return None
        return json.dumps(response), 200

    def process_batch_request(self, requests):
        """Process a batch of JSON-RPC requests."""
        if not requests:
            return json.dumps(self.error_response(-32600, "Invalid Request: batch array must not be empty", None)), 200

        responses = [r for r in (self.handle_one(item) for item in requests) if r is not None]
        if not responses:  # every element was a notification
            return None
        return json.dumps(responses), 200

    def handle_one(self, json_data):
        """Handle a single JSON-RPC request object, returning a response dict, or None for a notification."""
        try:
            if not isinstance(json_data, dict):
                raise JSONRPCException(-32600, "Invalid Request", None)
            self.validate_jsonrpc_version(json_data)
            # A missing 'id' key means notification. "id": null IS a request
            # (with a null id) per spec, even though clients SHOULD avoid it.
            if 'id' not in json_data:
                self.handle_notification(json_data)
                return None

            method, params = self.get_method_and_params(json_data)
            result = self.invoke_method(method, params, json_data)
            return self.success_response(result, json_data['id'])
        except JSONRPCException as e:
            return self.error_response(e.code, e.message, e.id)

    def parse_request_data(self, data):
        """Parse the request data."""
        try:
            return json.loads(data.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise JSONRPCException(-32700, 'Parse error', None) from e

    def validate_jsonrpc_version(self, json_data):
        """Validate the JSON-RPC version."""
        if json_data.get('jsonrpc') != '2.0':
            raise JSONRPCException(-32600, "Invalid Request: JSON-RPC version must be '2.0'", json_data.get('id'))

    def handle_notification(self, json_data):
        """Execute the method for a JSON-RPC notification. Errors are swallowed: notifications never get a response."""
        method = self.methods.get(json_data.get('method'))
        if method is None:
            return
        try:
            self.invoke_method(method, json_data.get('params'), json_data)
        except JSONRPCException:
            pass

    def get_method_and_params(self, json_data):
        """Get the method and params from the JSON-RPC request."""
        method_name = json_data.get('method')
        if not isinstance(method_name, str):
            raise JSONRPCException(-32600, "Invalid Request: Method name is required and must be a string.", json_data.get('id'))

        method = self.methods.get(method_name)
        if not method:
            raise JSONRPCException(-32601, "Method not found", json_data.get('id'))

        return method, json_data.get('params')

    def invoke_method(self, method, params, json_data):
        """Invoke the method with the given params."""
        try:
            if params is None:
                return method()
            elif isinstance(params, list):
                return method(*params)
            elif isinstance(params, dict):
                return method(**params)
            else:
                raise JSONRPCException(-32602, "Invalid params", json_data.get('id'))
        except TypeError as e:
            raise JSONRPCException(-32602, "Invalid params", json_data.get('id')) from e
        except JSONRPCException:
            raise
        except Exception as e:
            raise JSONRPCException(-32603, "Internal error", json_data.get('id')) from e

    def success_response(self, result, id_):
        """Build a successful JSON-RPC response object."""
        return {"jsonrpc": "2.0", "result": result, "id": id_}

    def error_response(self, code, message, id_):
        """Build a JSON-RPC error response object."""
        return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id_}


def run(
    server_class=ThreadingHTTPServer,
    handler_class=JSONRPCServer,
    address='',
    port=8000
):
    """Run the JSON-RPC server."""
    server_address = (address, port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd on port {port}...')
    httpd.serve_forever()
