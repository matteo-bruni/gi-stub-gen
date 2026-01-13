from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema
from gi_stub_gen.schema.function import FunctionSchema


GENUM_SCHEMA = ClassSchema(
    namespace="GObject",
    name="GEnum",
    super=["enum.IntEnum"],
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
            is_property=True,
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
            is_property=True,
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
