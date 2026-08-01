"""JSON-RPC 2.0 server implementation (stdlib only)."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
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

    # A lying or hostile Content-Length must not be able to park a thread on a
    # read that never completes, or ask for a gigabyte of memory.
    max_content_length = 10 * 1024 * 1024
    timeout = 30

    # Requires an accurate Content-Length on every response, which do_POST sends.
    protocol_version = 'HTTP/1.1'

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Own dict, seeded from the parent: a subclass must not mutate the base
        # class's registry, but it must still inherit what was registered there.
        cls.methods = dict(cls.methods)

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
        body = response.encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        """Read the request body using Content-Length."""
        try:
            content_length = int(self.headers.get('Content-Length'))
        except (TypeError, ValueError):
            raise JSONRPCException(-32600, "Invalid Request: Content-Length header is required", None)
        if content_length < 0:
            raise JSONRPCException(-32600, "Invalid Request: Content-Length must not be negative", None)
        if content_length > self.max_content_length:
            raise JSONRPCException(
                -32600,
                f"Invalid Request: body exceeds max_content_length ({self.max_content_length} bytes)",
                None,
            )
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
            self.validate_id(json_data['id'])

            method, params = self.get_method_and_params(json_data)
            result = self.invoke_method(method, params, json_data)
            return self.serializable_success(result, json_data['id'])
        except JSONRPCException as e:
            return self.error_response(e.code, e.message, e.id)

    @staticmethod
    def validate_id(id_):
        """The spec allows only String, Number or Null for `id`.

        `bool` is excluded deliberately: it is an `int` subclass in Python but
        is not a JSON number.
        """
        if isinstance(id_, bool) or not isinstance(id_, (str, int, float, type(None))):
            raise JSONRPCException(-32600, "Invalid Request: id must be a string, number, or null", None)

    def serializable_success(self, result, id_):
        """Build the success response, failing this request alone if it cannot
        be serialized.

        Serializing here rather than at the batch level means a method that
        returns a `set` or a `datetime` produces one -32603 instead of taking
        every other response in the batch down with it.
        """
        response = self.success_response(result, id_)
        try:
            json.dumps(response)
        except (TypeError, ValueError) as e:
            raise JSONRPCException(-32603, "Internal error: result is not JSON-serializable", id_) from e
        return response

    def parse_request_data(self, data):
        """Parse the request data.

        A body that is not valid UTF-8 is a parse error like any other; letting
        UnicodeDecodeError escape here dropped the connection instead.
        """
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
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
        """Invoke the method with the given params.

        Arity is checked against the signature *before* the call, so a TypeError
        raised inside the method body is reported as -32603 (Internal error)
        rather than being blamed on the caller's params as -32602.
        """
        id_ = json_data.get('id')
        if params is None:
            args, kwargs = (), {}
        elif isinstance(params, list):
            args, kwargs = tuple(params), {}
        elif isinstance(params, dict):
            args, kwargs = (), params
        else:
            raise JSONRPCException(-32602, "Invalid params", id_)

        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            # ponytail: some builtins expose no signature; skip the pre-check
            # and let the call itself decide. Only affects error-code fidelity.
            signature = None
        if signature is not None:
            try:
                signature.bind(*args, **kwargs)
            except TypeError as e:
                raise JSONRPCException(-32602, "Invalid params", id_) from e

        try:
            return method(*args, **kwargs)
        except JSONRPCException:
            raise
        except Exception as e:
            raise JSONRPCException(-32603, "Internal error", id_) from e

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
