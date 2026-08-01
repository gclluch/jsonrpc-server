# server_fixture.py

from jsonrpc_server import JSONRPCException, run, register_method

def sum_numbers(*args, **kwargs):
    # If positional arguments are used
    if args:
        return sum(args)
    # If named arguments are used
    return kwargs['a'] + kwargs['b']

def say_hello(name):
    return f"Hello, {name}!"

def ping():
    return "pong"

def boom():
    raise ValueError("boom")

def type_error_inside():
    # A TypeError raised by the body, not by argument binding. It must be
    # reported as -32603, not blamed on the caller's params as -32602.
    return "a" + 1

def nonserializable():
    # json.dumps cannot encode a set: the failure must be scoped to this one
    # request rather than taking a whole batch down.
    return {1, 2, 3}

# Register methods with the server

def app_error():
    # An application-level failure in the spec's server-defined range. The
    # handler cannot know the request id, so the server must attach it.
    raise JSONRPCException(-32001, "Application specific error")


register_method('sum', sum_numbers)
register_method('hello', say_hello)
register_method('ping', ping)  # Register the ping method
register_method('boom', boom)  # Always raises, for testing -32603
register_method('type_error_inside', type_error_inside)
register_method('nonserializable', nonserializable)
register_method('app_error', app_error)

# This will run the server when the file is executed
if __name__ == "__main__":
    run(address='localhost', port=8000)
