from .server import JSONRPCException, JSONRPCServer, run

def register_method(name, method):
    """Register a method to be exposed by the JSON-RPC server."""
    JSONRPCServer.register_method(name, method)

__all__ = ["JSONRPCException", "JSONRPCServer", "run", "register_method"]
