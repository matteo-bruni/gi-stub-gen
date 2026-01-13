from gi_stub_gen.schema.class_ import ClassSchema


CLASS_GTYPE_META = ClassSchema(
    namespace="GObject",
    name="GTypeMeta",
    super=["type", "GType"],
    docstring="Metaclass to make a Python class compatible with GObject.GType arguments during static analysis.\n\n"
    "In PyGObject runtime, a Python wrapper class (e.g., Gst.FractionRange) can be directly passed "
    "to functions expecting a GObject.GType (like `Gst.Structure.has_field_typed`), because the "
    "binding automatically resolves the `__gtype__` property.\n\n"
    "However, static type checkers (e.g., Pylance, MyPy) strictly expect an *instance* of "
    "GObject.GType, not a Python *class type*, causing false positive errors.\n\n"
    "By inheriting from both `type` and `GObject.GType`, this metaclass ensures that the "
    "class object itself is recognized as an instance of GObject.GType by type checkers, "
    "bridging the gap between the Python type system and GObject introspection without "
    "affecting runtime behavior. [manual-override]",
    props=[],
    required_gi_import=None,
    fields=[],
    methods=[],
    python_methods=[],
    signals=[],
    extra=[],
    is_deprecated=False,
)
"""GTypeMeta is created as a manual override to help static analysis tools. 
It does not exist in the runtime as a separate class."""
