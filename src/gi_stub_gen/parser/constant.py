from __future__ import annotations

# import gi

import gi._gi as GI  # type: ignore
from gi_stub_gen.utils import catch_gi_deprecation_warnings  # type: ignore

# from gi._gi import Repository  # type: ignore
from gi.repository import GObject
from typing import Any


from gi_stub_gen.schema.constant import VariableSchema


def parse_constant(
    parent: str,
    name: str,  # name of the attribute
    obj: Any,  # actual object to be parsed
    docstring: str | None,
):
    """
    Parse values and return a VariableSchema.
    Return None if the object is not a module constant.

    Args:
        parent (str): parent module name
        name (str): name of the attribute
        obj (Any): object to be parsed

    Returns:
        VariableSchema | None
    """

    _gi_type = type(obj)

    if _gi_type in (int, str, float, dict, tuple, list):
        # if is_py_builtin_type(_gi_type):
        return VariableSchema.from_gi_object(
            obj=obj,
            namespace=parent,
            name=name,
            docstring=docstring,
            deprecation_warnings=None,
        )

    w = catch_gi_deprecation_warnings(parent, name)
    # check if it is a constant from an enum/flag
    if hasattr(obj, "__info__"):
        info = getattr(obj, "__info__")
        # both enums and flags have __info__ attribute of type EnumInfo
        # example, this is a flag:
        # type(getattr(Gst.BUFFER_COPY_METADATA, "__info__")) == GI.EnumInfo
        if type(info) is GI.EnumInfo:
            # if info.is_flags():
            # at this point this can be the "flags" class or an attribute
            # with a value of the flag class
            # if it is an attribute it is an instance of GObject.GFlags
            if isinstance(obj, (GObject.GFlags, GObject.GEnum)):
                # or info.get_g_type().parent.name == "GFlags"
                assert obj.is_integer(), f"{name} is not an enum/flag?"
                return VariableSchema.from_gi_object(
                    obj=obj,
                    namespace=parent,
                    name=name,
                    docstring=docstring,
                    deprecation_warnings=w,
                )

    # TODO: handle GType elements (which lacks __info__ attribute)
    if isinstance(obj, GObject.GType):
        # GType is a type, not a value
        # so we can not parse it as a constant
        # but we can parse it as an enum/flag
        return VariableSchema.from_gi_object(
            obj=obj,
            namespace=parent,
            name=name,
            docstring=docstring,
            deprecation_warnings=w,
        )

    return None
