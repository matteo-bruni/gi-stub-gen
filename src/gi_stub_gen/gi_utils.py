import importlib
import keyword
from typing import Any
import logging
import gi
import gi._gi as GI  # type: ignore
from gi._gi import Repository  # pyright: ignore[reportMissingImports]
from gi.repository import GObject  # pyright: ignore[reportMissingModuleSource]
from gi.repository import GIRepository  # pyright: ignore[reportMissingModuleSource]


logger = logging.getLogger(__name__)


def get_gi_array_length(
    gi_type_info: GI.TypeInfo,
) -> int:
    # removed in pygobject 3.54.0?? was present in 3.50.0
    # logger.warning(
    #     f"Could not get array length for argument {obj.get_name()}: {e}"
    # )
    # https://valadoc.org/gobject-introspection-1.0/GI.TypeInfo.get_array_length.html
    # the array length, or -1 if the type is not an array
    # somehow in the newer pygobject this method is missing if not an array

    if hasattr(gi_type_info, "get_array_length"):
        return gi_type_info.get_array_length()
    return -1


def get_safe_gi_array_length(
    gi_type: GI.TypeInfo,
) -> int:
    """
    Restituisce l'indice dell'argomento che rappresenta la lunghezza dell'array.
    Restituisce -1 se il tipo non è un array o se non ha una lunghezza esplicita.
    """
    # Prima verifichiamo se è effettivamente un array
    # GIRepository.TypeTag.ARRAY è l'enum standard
    try:
        tag = gi_type.get_tag()
        if tag != GIRepository.TypeTag.ARRAY:
            return -1
    except AttributeError:
        # Se non possiamo nemmeno ottenere il tag, assumiamo non sia un array
        return -1

    # Ora proviamo a ottenere la lunghezza
    try:
        return gi_type.get_array_length()
    except AttributeError:
        # Fallback per versioni dove il metodo manca su certi oggetti
        return -1


def get_gi_type_info(
    obj: Any,
) -> GI.TypeInfo | GIRepository.TypeInfo:
    """
    Recovers safely the TypeInfo from an ArgInfo or similar object.
    Handles the discrepancy between PyGObject versions (get_type vs get_type_info).
    """

    # was present in 3.50.0 ??
    if hasattr(obj, "get_type"):
        return obj.get_type()

    if hasattr(obj, "get_type_info"):
        return obj.get_type_info()

    # if it is already a TypeInfo, return it
    if isinstance(obj, GIRepository.TypeInfo):  # type: ignore
        return obj

    raise AttributeError(f"Could not recover TypeInfo from object: {obj} ({type(obj)})")


def is_property_nullable_safe(prop_info: Any) -> bool:
    """
    Since cant access may_return_null on property directly,
    we need to implement some heuristics to determine if a property can be None.
    Returns True if the property can be None, False otherwise.
    1. Check type tag: if primitive, return False
    2. For complex types, assume True (nullable) if no direct info is available.
    """

    type_info = get_gi_type_info(prop_info)
    tag = type_info.get_tag()
    NON_NULLABLE_TAGS = {
        GIRepository.TypeTag.BOOLEAN,
        GIRepository.TypeTag.INT8,
        GIRepository.TypeTag.UINT8,
        GIRepository.TypeTag.INT16,
        GIRepository.TypeTag.UINT16,
        GIRepository.TypeTag.INT32,
        GIRepository.TypeTag.UINT32,
        GIRepository.TypeTag.INT64,
        GIRepository.TypeTag.UINT64,
        GIRepository.TypeTag.UTF8,
        GIRepository.TypeTag.FLOAT,
        GIRepository.TypeTag.DOUBLE,
        GIRepository.TypeTag.UNICHAR,
    }

    if tag in NON_NULLABLE_TAGS:
        return False

    return True
