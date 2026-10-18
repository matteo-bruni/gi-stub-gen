"""PyGObject 3.58.1's _warn_init hides the property constructor signature."""

from gi_stub_gen.schema.function import FunctionSchema


def build_dbus_connection_init(namespace: str, cls: type) -> FunctionSchema:
    # Defer the parser import to avoid a registry/parser cycle and import-time GI work.
    from gi_stub_gen.parser.class_ import create_init_method

    method = create_init_method(namespace, cls)
    if method is None:
        raise ValueError(f"Cannot build {namespace}.{cls.__name__}.__init__ from GObject properties")
    method.docstring = (
        f"{method.docstring}\n\n"
        "PyGObject warns that Gio.DBusConnection should not be instantiated directly. "
        "Use Gio.DBusConnection.new_sync or Gio.DBusConnection.new_for_address_sync "
        "(or their asynchronous counterparts) to create an initialized connection."
    )
    return method
