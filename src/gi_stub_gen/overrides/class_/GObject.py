"""
Manual overrides for GObject.GEnum and GObject.GFlags
to represent them as subclasses of enum.IntEnum and enum.IntFlag respectively.

They are manually put inside GObject during alias parsing.
This is because in GObject module they are an alias to gi._gi.GEnum and gi._gi.GFlags

"""

from gi_stub_gen.schema.builtin_function import ArgKind, BuiltinFunctionArgumentSchema, BuiltinFunctionSchema
from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema
from gi_stub_gen.schema.function import FunctionSchema, FunctionArgumentSchema

GENUM_SCHEMA = ClassSchema(
    namespace="GObject",
    name="GEnum",
    bases=["enum.IntEnum"],
    docstring="From pygobject 3.52 GEnum are integrated with enum.IntEnum"
    " see https://pygobject.gnome.org/changelog.html [manual-override]",
    props=[],
    required_gi_import="enum",
    fields=[
        ClassFieldSchema(
            name="__gtype__",
            type_hint_name="GType",
            type_hint_namespace="GObject",
            may_be_null=False,
            line_comment=None,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The GType of the enum.",
            is_readable=True,
            is_writable=False,
        ),
    ],
    methods=[
        FunctionSchema(
            name="value_name",
            namespace="",
            is_method=True,
            is_class_member=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The name of the value.",
            args=[],
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=True,
            is_setter=False,
            may_return_null=False,
            return_hint="str",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="FunctionInfo",
            is_overload=False,
        ),
        FunctionSchema(
            name="value_nick",
            namespace="",
            is_method=True,
            is_class_member=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nickname of the value.",
            args=[],
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=True,
            is_setter=False,
            may_return_null=False,
            return_hint="str",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="FunctionInfo",
            is_overload=False,
        ),
    ],
    python_methods=[],
    signals=[],
    extra=[],
    is_deprecated=False,
)
'''
Representation of GEnum for manual override

class GEnum(IntEnum):
    """
    From pygobject 3.52 GEnum are integrated with enum.IntEnum
    see https://pygobject.gnome.org/changelog.html
    """

    __gtype__: GObject.GType
    value_name: str
    """The name of the value."""

    value_nick: str
    """The nickname of the value."""
'''
GFLAG_SCHEMA = ClassSchema(
    namespace="GObject",
    name="GFlags",
    bases=["enum.IntFlag"],
    docstring="From pygobject 3.52 GFlags "
    "are integrated with enum.Flag"
    " see https://pygobject.gnome.org/changelog.html [manual-override]",
    required_gi_import="enum",
    props=[],
    fields=[
        ClassFieldSchema(
            name="__gtype__",
            type_hint_name="GType",
            type_hint_namespace="GObject",
            may_be_null=False,
            line_comment=None,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The GType of the enum.",
            is_readable=True,
            is_writable=False,
        ),
    ],
    methods=[
        FunctionSchema(
            name="first_value_name",
            namespace="",
            is_method=True,
            is_class_member=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The name of the first value.",
            args=[],
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=True,
            is_setter=False,
            may_return_null=False,
            return_hint="str",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="FunctionInfo",
            is_overload=False,
        ),
        FunctionSchema(
            name="first_value_nick",
            namespace="",
            is_method=True,
            is_class_member=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nickname of the first value.",
            args=[],
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=True,
            is_setter=False,
            may_return_null=False,
            return_hint="str",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="FunctionInfo",
            is_overload=False,
        ),
        FunctionSchema(
            name="value_names",
            namespace="",
            is_method=True,
            is_class_member=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The names of the values.",
            args=[],
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=True,
            is_setter=False,
            may_return_null=False,
            return_hint="list[str]",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="FunctionInfo",
            is_overload=False,
        ),
        FunctionSchema(
            name="value_nicks",
            namespace="",
            is_method=True,
            is_class_member=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nicknames of the values.",
            args=[],
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=True,
            is_setter=False,
            may_return_null=False,
            return_hint="list[str]",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="FunctionInfo",
            is_overload=False,
        ),
    ],
    python_methods=[],
    signals=[],
    extra=[],
    is_deprecated=False,
)
'''
Representation of GFlags for manual override

class GFlags(IntFlag):
    """
    From pygobject 3.52 GFlags are integrated with enum.Flag
    see https://pygobject.gnome.org/changelog.html
    """

    __gtype__: GObject.GType
    first_value_name: str
    first_value_nick: str
    value_names: list[str]
    value_nicks: list[str]
'''


OBJECT_EMIT = FunctionSchema(
    name="emit",
    namespace="GObject",
    is_method=True,
    is_class_member=True,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="Emit a signal.",
    args=[
        FunctionArgumentSchema(
            namespace="GObject",
            name="detailed_signal",
            direction="IN",
            is_callback=False,
            may_be_null=False,
            is_optional=False,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="str",
            py_type_namespace=None,
            line_comment=None,
            default_value=None,
            is_pointer=False,
        ),
        FunctionArgumentSchema(
            namespace="GObject",
            name="*args",
            direction="IN",
            is_callback=False,
            may_be_null=False,
            is_optional=False,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="Any",
            py_type_namespace="typing",
            line_comment=None,
            default_value=None,
            is_pointer=False,
        ),
    ],
    is_callback=False,
    can_throw_gerror=False,
    is_async=False,
    is_constructor=False,
    is_getter=False,
    is_setter=False,
    may_return_null=False,
    return_hint="Any",
    return_hint_namespace="typing",
    skip_return=False,
    wrap_vfunc=False,
    line_comment=None,
    function_type="FunctionInfo",
    is_overload=False,
)

# OBJECT_DISCONNECT = FunctionSchema(
#     name="disconnect",
#     namespace="GObject",
#     is_method=True,
#     is_deprecated=False,
#     deprecation_warnings=None,
#     docstring="Disconnect a signal handler.",
#     args=[
#         FunctionArgumentSchema(
#             namespace="GObject",
#             name="handler_id",
#             direction="IN",
#             is_callback=False,
#             may_be_null=False,
#             is_optional=False,
#             is_deprecated=False,
#             is_caller_allocates=False,
#             tag_as_string="",
#             get_array_length=-1,
#             py_type_name="int",
#             py_type_namespace=None,
#             line_comment=None,
#             default_value=None,
#         ),
#     ],
#     is_callback=False,
#     can_throw_gerror=False,
#     is_async=False,
#     is_constructor=False,
#     is_getter=False,
#     is_setter=False,
#     may_return_null=False,
#     return_hint="None",
#     return_hint_namespace=None,
#     skip_return=False,
#     wrap_vfunc=False,
#     line_comment=None,
#     function_type="FunctionInfo",
#     is_overload=False,
# )

# OBJECT_HANDLER_BLOCK = FunctionSchema(
#     name="handler_block",
#     namespace="GObject",
#     is_method=True,
#     is_deprecated=False,
#     deprecation_warnings=None,
#     docstring="Block a signal handler.",
#     args=[
#         FunctionArgumentSchema(
#             namespace="GObject",
#             name="handler_id",
#             direction="IN",
#             is_callback=False,
#             may_be_null=False,
#             is_optional=False,
#             is_deprecated=False,
#             is_caller_allocates=False,
#             tag_as_string="",
#             get_array_length=-1,
#             py_type_name="int",
#             py_type_namespace=None,
#             line_comment=None,
#             default_value=None,
#         ),
#     ],
#     is_callback=False,
#     can_throw_gerror=False,
#     is_async=False,
#     is_constructor=False,
#     is_getter=False,
#     is_setter=False,
#     may_return_null=False,
#     return_hint="None",
#     return_hint_namespace=None,
#     skip_return=False,
#     wrap_vfunc=False,
#     line_comment=None,
#     function_type="FunctionInfo",
#     is_overload=False,
# )

# OBJECT_HANDLER_UNBLOCK = FunctionSchema(
#     name="handler_unblock",
#     namespace="GObject",
#     is_method=True,
#     is_deprecated=False,
#     deprecation_warnings=None,
#     docstring="Unblock a signal handler.",
#     args=[
#         FunctionArgumentSchema(
#             namespace="GObject",
#             name="handler_id",
#             direction="IN",
#             is_callback=False,
#             may_be_null=False,
#             is_optional=False,
#             is_deprecated=False,
#             is_caller_allocates=False,
#             tag_as_string="",
#             get_array_length=-1,
#             py_type_name="int",
#             py_type_namespace=None,
#             line_comment=None,
#             default_value=None,
#         ),
#     ],
#     is_callback=False,
#     can_throw_gerror=False,
#     is_async=False,
#     is_constructor=False,
#     is_getter=False,
#     is_setter=False,
#     may_return_null=False,
#     return_hint="None",
#     return_hint_namespace=None,
#     skip_return=False,
#     wrap_vfunc=False,
#     line_comment=None,
#     function_type="FunctionInfo",
#     is_overload=False,
# )

OBJECT_WEAK_REF = FunctionSchema(
    name="weak_ref",
    namespace="GObject",
    is_method=True,
    is_class_member=True,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="Creates a weak reference to the object.",
    args=[
        FunctionArgumentSchema(
            namespace="GObject",
            name="callback",
            direction="IN",
            is_callback=True,
            may_be_null=True,
            is_optional=True,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="Callable[[typing.Any], None]",
            py_type_namespace="typing",
            line_comment=None,
            default_value="None",
            is_pointer=False,
        ),
    ],
    is_callback=False,
    can_throw_gerror=False,
    is_async=False,
    is_constructor=False,
    is_getter=False,
    is_setter=False,
    may_return_null=False,
    return_hint="Any",
    return_hint_namespace="typing",
    skip_return=False,
    wrap_vfunc=False,
    line_comment=None,
    function_type="FunctionInfo",
    is_overload=False,
)

OBJECT_HANDLER_DEFAULT = FunctionSchema(
    name="handler_default",
    namespace="GObject",
    is_method=True,
    is_class_member=True,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="Set the default handler for a signal.",
    args=[
        FunctionArgumentSchema(
            namespace="GObject",
            name="callback",
            direction="IN",
            is_callback=True,
            may_be_null=True,
            is_optional=True,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="Callable[[typing.Any], None]",
            py_type_namespace="typing",
            line_comment=None,
            default_value="None",
            is_pointer=False,
        ),
    ],
    is_callback=False,
    can_throw_gerror=False,
    is_async=False,
    is_constructor=False,
    is_getter=False,
    is_setter=False,
    may_return_null=False,
    return_hint="None",
    return_hint_namespace=None,
    skip_return=False,
    wrap_vfunc=False,
    line_comment=None,
    function_type="FunctionInfo",
    is_overload=False,
)


# def get_property(self, property_name: str) -> any: ...

OBJECT_GET_PROPERTY = FunctionSchema(
    name="get_property",
    namespace="GObject",
    is_method=True,
    is_class_member=True,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="Get a property value by name.",
    args=[
        FunctionArgumentSchema(
            namespace="GObject",
            name="property_name",
            direction="IN",
            is_callback=False,
            may_be_null=False,
            is_optional=False,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="str",
            py_type_namespace=None,
            line_comment=None,
            default_value=None,
            is_pointer=False,
        ),
    ],
    is_callback=False,
    can_throw_gerror=False,
    is_async=False,
    is_constructor=False,
    is_getter=False,
    is_setter=False,
    may_return_null=False,
    return_hint="Any",
    return_hint_namespace="typing",
    skip_return=False,
    wrap_vfunc=False,
    line_comment=None,
    function_type="FunctionInfo",
    is_overload=False,
)

# def set_property(self, property_name: str, value: any) -> None: ...

OBJECT_SET_PROPERTY = FunctionSchema(
    name="set_property",
    namespace="GObject",
    is_method=True,
    is_class_member=True,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="Set a property value by name.",
    args=[
        FunctionArgumentSchema(
            namespace="GObject",
            name="property_name",
            direction="IN",
            is_callback=False,
            may_be_null=False,
            is_optional=False,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="str",
            py_type_namespace=None,
            line_comment=None,
            default_value=None,
            is_pointer=False,
        ),
        FunctionArgumentSchema(
            namespace="GObject",
            name="value",
            direction="IN",
            is_callback=False,
            may_be_null=False,
            is_optional=False,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="object",
            py_type_namespace="builtins",
            line_comment=None,
            default_value=None,
            is_pointer=False,
        ),
    ],
    is_callback=False,
    can_throw_gerror=False,
    is_async=False,
    is_constructor=False,
    is_getter=False,
    is_setter=False,
    may_return_null=False,
    return_hint="None",
    return_hint_namespace=None,
    skip_return=False,
    wrap_vfunc=False,
    line_comment=None,
    function_type="FunctionInfo",
    is_overload=False,
)


CLASS_GTYPE_META = ClassSchema(
    namespace="GObject",
    name="GTypeMeta",
    bases=["type", "GType"],
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
# import typing

# # We define a TypeVar to capture the return type of the property (e.g., int, str).
# _T = typing.TypeVar('_T')

# getter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = (None,)
# setter: typing.Optional[typing.Callable[[typing.Any, typing.Any], None]] = (None,)
# type: typing.Type[typing.Any] | None = (None,)
# default: typing.Any = (None,)
# nick: str = ("",)
# blurb: str = ("",)
# flags: int = (PARAM_READWRITE,)
# minimum: typing.Any = (None,)
# maximum: typing.Any = (None,)

#     def __init__(
#         self,
#         type: typing.Any = None,
#         default: typing.Any = None,
#         nick: str = None,
#         blurb: str = None,
#         flags: typing.Any = None,
#         minimum: typing.Any = None,
#         maximum: typing.Any = None,
#         # Add '...' to allow any other GParamSpec arguments not explicitly listed
#         **kwargs: typing.Any
#     ) -> None:
#         """
#         The __init__ method handles the arguments passed to the decorator factory.
#         Example: @GObject.Property(type=int, default=10)
#         """
#         ...

#     def __call__(self, fget: typing.Callable[[typing.Any], _T]) -> "Property":
#         """
#         This method is required because GObject.Property is used as a decorator factory.

#         When you write:
#             @GObject.Property(type=int)
#             def my_prop(self): ...

#         Python first instantiates Property(...), and then calls that instance
#         passing the function 'my_prop' as 'fget'.

#         Returns: 'self' (the Property instance) so that .setter can be chained.
#         """
#         ...

#     def setter(self, fset: typing.Callable[[typing.Any, _T], None]) -> "Property":
#         """
#         Explicit definition of the setter.

#         Even though we inherit from 'property', defining this explicitly ensures
#         Pylance resolves the "@my_prop.setter" syntax correctly without
#         "Attribute 'setter' is unknown" errors.
#         """
#         ...
#     def getter(self, fget: typing.Callable[[typing.Any], _T]) -> "Property":
#         """
#         Standard getter definition matching the property protocol.
#         """
#         ...

#     # --- Descriptor Protocol ---
#     # These ensure Pylance understands that accessing the property on an instance
#     # returns the value (_T), not the Property object itself.
#     def __get__(self, instance: typing.Any, owner: typing.Any) -> _T: ...
#     def __set__(self, instance: typing.Any, value: _T) -> None: ...

CLASS_PROPERTY = ClassSchema(
    namespace="GObject",
    name="Property",
    bases=["property"],
    docstring="Stub for GObject.Property.\n\n"
    "CRITICAL: This class inherits from the built-in 'property' class.\n"
    "This tells static analysis tools (Pylance/MyPy) that this object acts as a \n"
    'descriptor, preventing the "Method declaration is obscured" error when '
    "applying the decorator over a method.\n\n",
    props=[],
    required_gi_import="typing",
    fields=[],
    methods=[],
    python_methods=[
        BuiltinFunctionSchema(
            name="__init__",
            namespace="GObject",
            is_async=False,
            is_from_class=True,
            is_classmethod=False,
            is_staticmethod=False,
            docstring=None,
            return_hint_name="None",
            return_hint_namespace=None,
            return_is_optional=False,
            params=[
                BuiltinFunctionArgumentSchema(
                    name="type",
                    kind=ArgKind.POSITIONAL_OR_KEYWORD,
                    type_hint_name="Any",
                    type_hint_namespace="typing",
                    is_optional=True,
                    default_value="None",
                    line_comment=None,
                ),
            ],
        ),
    ],
    # args=[], #BuiltinFunctionArgumentSchema
    signals=[],
    extra=[],
    is_deprecated=False,
)
