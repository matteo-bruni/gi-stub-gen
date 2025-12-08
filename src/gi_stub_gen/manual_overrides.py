from enum import IntEnum, IntFlag

from gi.repository import GObject

from gi_stub_gen.parser.gir import GirClassDocs
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
    attributes=[
        ClassAttributeSchema(
            name="__gtype__",
            type_hint="GType",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The GType of the enum.",
        ),
        ClassAttributeSchema(
            name="value_name",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The name of the value.",
        ),
        ClassAttributeSchema(
            name="value_nick",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nickname of the value.",
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
    props=[],
    attributes=[
        ClassAttributeSchema(
            name="__gtype__",
            type_hint="GType",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The GType of the flags.",
        ),
        ClassAttributeSchema(
            name="first_value_name",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The name of the first value.",
        ),
        ClassAttributeSchema(
            name="first_value_nick",
            type_hint="str",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nickname of the first value.",
        ),
        ClassAttributeSchema(
            name="value_names",
            type_hint="list[str]",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The names of the values.",
        ),
        ClassAttributeSchema(
            name="value_nicks",
            type_hint="list[str]",
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="The nicknames of the values.",
        ),
    ],
    methods=[],
    extra=[],
    is_deprecated=False,
)
