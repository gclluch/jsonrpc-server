"""Method-registry semantics: no HTTP, no server process."""

from jsonrpc_server.server import JSONRPCServer


def test_subclass_inherits_registrations_without_mutating_the_base():
    JSONRPCServer.register_method("base_only", lambda: "base")

    class Child(JSONRPCServer):
        pass

    Child.register_method("child_only", lambda: "child")

    assert "base_only" in Child.methods, "subclass should inherit what the base registered"
    assert "child_only" not in JSONRPCServer.methods, "subclass must not write into the base registry"

    JSONRPCServer.methods.pop("base_only", None)


def test_rpc_prefix_is_reserved():
    try:
        JSONRPCServer.register_method("rpc.internal", lambda: None)
    except ValueError:
        return
    raise AssertionError("names beginning with 'rpc.' are reserved by the spec")
