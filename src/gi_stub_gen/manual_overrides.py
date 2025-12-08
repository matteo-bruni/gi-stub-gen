from enum import IntEnum, IntFlag

from gi.repository import GObject
from gi_stub_gen.schema.class_ import ClassAttributeSchema, ClassSchema


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


MANUAL_GENUM_SCHEMA = ClassSchema(
    namespace="GObject",
    name="GEnum",
    bases=["enum.IntEnum"],
    docstring="From pygobject 3.52 GEnum are integrated with enum.IntEnum"
    " see https://pygobject.gnome.org/changelog.html",
    props=[],
    required_gi_import="GObject",
    attributes=[
        ClassAttributeSchema(
            name="__gtype__",
            type_hint="GType",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The GType of the enum.",
            required_gi_import="GObject",
        ),
        ClassAttributeSchema(
            name="value_name",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The name of the value.",
            required_gi_import=None,
        ),
        ClassAttributeSchema(
            name="value_nick",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nickname of the value.",
            required_gi_import=None,
        ),
    ],
    methods=[],
    extra=[],
    is_deprecated=False,
)


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


MANUAL_GFLAG_SCHEMA = ClassSchema(
    namespace="GObject",
    name="GFlags",
    bases=["enum.IntFlag"],
    docstring="From pygobject 3.52 GFlags "
    "are integrated with enum.Flag"
    " see https://pygobject.gnome.org/changelog.html",
    required_gi_import="GObject",
    props=[],
    attributes=[
        ClassAttributeSchema(
            name="__gtype__",
            type_hint="GType",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The GType of the flags.",
            required_gi_import="GObject",
        ),
        ClassAttributeSchema(
            name="first_value_name",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The name of the first value.",
            required_gi_import=None,
        ),
        ClassAttributeSchema(
            name="first_value_nick",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nickname of the first value.",
            required_gi_import=None,
        ),
        ClassAttributeSchema(
            name="value_names",
            type_hint="list[str]",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The names of the values.",
            required_gi_import=None,
        ),
        ClassAttributeSchema(
            name="value_nicks",
            type_hint="list[str]",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nicknames of the values.",
            required_gi_import=None,
        ),
    ],
    methods=[],
    extra=[],
    is_deprecated=False,
)
