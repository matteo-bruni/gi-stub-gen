from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema
from gi_stub_gen.schema.function import FunctionSchema


GFLAG_SCHEMA = ClassSchema(
    namespace="GObject",
    name="GFlags",
    super=["enum.IntFlag"],
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
            is_property=True,
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
            is_property=True,
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
