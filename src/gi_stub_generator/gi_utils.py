import importlib
import keyword
from typing import Any
import logging
import gi
import gi._gi as GI  # type: ignore
from gi._gi import Repository  # pyright: ignore[reportMissingImports]
from gi.repository import GObject  # pyright: ignore[reportMissingModuleSource]
from gi.repository import GIRepository  # pyright: ignore[reportMissingModuleSource]

# from typing import Sequence, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi_stub_generator.schema.function import FunctionArgumentSchema

logger = logging.getLogger(__name__)


def get_gi_array_length(gi_type_info: GI.TypeInfo) -> int:
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


def get_safe_gi_array_length(gi_type: GI.TypeInfo) -> int:
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


def get_gi_type_info(obj: GI.ArgInfo) -> GI.TypeInfo:
    """
    Recupera in modo sicuro il TypeInfo da un ArgInfo o oggetto simile.
    Gestisce la discrepanza tra le versioni di PyGObject (get_type vs get_type_info).
    """
    # Tentativo 1: API standard moderna
    if hasattr(obj, "get_type"):
        return obj.get_type()

    # Tentativo 2: API alternativa (talvolta presente in vecchie versioni o struct specifici)
    if hasattr(obj, "get_type_info"):
        return obj.get_type_info()

    # Tentativo 3: Se l'oggetto è già un TypeInfo (caso ricorsivo o errore chiamante)
    if isinstance(obj, GIRepository.TypeInfo):  # type: ignore
        return obj
    # if hasattr(obj, "__info__"):
    #     return obj.__info__

    # breakpoint()
    raise AttributeError(
        f"Impossibile recuperare TypeInfo dall'oggetto: {obj} ({type(obj)})"
    )
