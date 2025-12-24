from __future__ import annotations


from pydantic import SerializerFunctionWrapHandler
from pydantic.functional_serializers import WrapSerializer
from typing import Annotated, Any


# Custom Type Value Any for Any or None type
# we add a custom serializer to handle the serialization of Any type
# if it not serializable, it will fallback to str(v)
# used for debugging purposes, i.e a variable = dict(gobject_values)
# this is due to some classes having attributes that are not serializable
def ser_variable_wrap(v: Any, fun: SerializerFunctionWrapHandler):
    # return f'{nxt(v + 1):,}'
    try:
        return fun(v)
    except Exception:
        # logger.warning(f"[WARNING] Error serializing variable: {e}: {v}")
        # print("[DEBUG] Variable value:", v)
        return str(v)  # Fallback to string representation
    # return fun(v)


ValueAny = Annotated[Any | None, WrapSerializer(ser_variable_wrap, when_used="json")]
