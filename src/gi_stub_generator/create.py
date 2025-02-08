from gi_stub_generator.parse import parse_constant, parse_function
from gi_stub_generator.schema import (
    Attribute,
    CallbackSchema,
    FunctionArgumentSchema,
    FunctionSchema,
    Module,
)
from gi_stub_generator.utils import gi_callback_to_py_type
import jinja2
from enum import Enum
from types import ModuleType
from typing import Any, Literal
import gi.docstring
from pydantic import ConfigDict
import gi
import gi._gi as GIRepository
from .docstring import generate_doc_string, _generate_callable_info_doc

gi.require_version("Gst", "1.0")


# Resources
# https://developer.gnome.org/documentation/guidelines/programming/introspection.html
# https://gi.readthedocs.io/en/latest/annotations/giannotations.html

from gi.repository import (  # noqa: E402, F401
    GLib,
    Gst,
    GObject,
)

# _build(m, args.module, overrides)
# m=Gst, module=Gst as string,
# build(parent: ObjectT, namespace: str, overrides: dict[str, str])
# Gst, Gst:str, dir(Gst)


# print(dir(Gst))

TEMPLATE = """from typing import Any
from typing import Callable
from typing import Literal
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar

from gi.repository import GLib
from gi.repository import GObject

{% for c in constants -%}
{{c.name}}: {{c.type}} = {{c.value_repr}}
{% endfor %}

{% for f in functions -%}
def {{f}}: ...
{% endfor %}


"""


def check_module(
    m: ModuleType,
):
    module_attributes = dir(m)

    module_name = m.__name__.split(".")[-1]
    module_constants: list[Attribute] = []
    module_functions: list[FunctionSchema] = []
    module_used_callbacks: list[FunctionSchema] = []
    # module_genums: list[Attribute] = []
    # module_gflags: list[Attribute] = []

    # map all module attributes to their types
    # has_info: dict[str, list[str]] = {}
    callbacks_found: list[GIRepository.TypeInfo] = []
    unknown_module_map_types: dict[str, list[str]] = {}
    for attribute_name in module_attributes:
        if attribute_name.startswith("__"):
            continue

        attribute = getattr(m, attribute_name)
        attribute_type = type(attribute)

        #########################################################################
        # check if the attribute is a constant
        #########################################################################

        c = parse_constant(
            parent=module_name,
            name=attribute_name,
            obj=attribute,
            obj_type=attribute_type,
        )
        if c:
            module_constants.append(c)
            continue

        #########################################################################
        # check if the attribute is a function
        #########################################################################

        if isinstance(attribute, GIRepository.VFuncInfo):
            # GIVFuncInfo
            # represents a virtual function.
            # A virtual function is a callable object that belongs to either a
            # GIObjectInfo or a GIInterfaceInfo.
            raise NotImplementedError("VFuncInfo not implemented")

        f = parse_function(attribute)
        if f:
            module_functions.append(f)
            callbacks_found.extend(f._gi_callbacks)

        # Check if it is a function ####################################################################################
        # gi.types.StructMeta
        #  ->  'AllocatorClass'

        # gi.types.GObjectMeta
        # ->  'Bin'

        # type (enum and flags here)
        # -> 'BinFlags', 'BufferCopyFlags', 'BufferFlags', 'BufferPoolAcquireFlags', 'BufferingMode'
        # prova .__info__.get_g_type().parent.name

        # check if the attribute is an enum
        attribute_type_name = attribute_type.__name__
        unknown_key = f"{attribute_type_name}[{attribute_type}]"
        if unknown_key in unknown_module_map_types:
            unknown_module_map_types[unknown_key].append(attribute_name)
        else:
            unknown_module_map_types[unknown_key] = [attribute_name]
            # module_map_types[f"{attribute_type_name}"] = [attribute_name]

        # also check if the attribute has __info__ attribute
        # if hasattr(getattr(m, attribute_name), "__info__"):
        #     if f"{attribute_type_name}" in has_info:
        #         has_info[f"{attribute_type_name}"].append(attribute_name)
        #     else:
        #         has_info[f"{attribute_type_name}"] = [attribute_name]

    # print(m)

    # print("Has Info")
    # for key, value in has_info.items():
    #     print(f"- {key}: {value}")
    #     print("\n")

    # print("Constants")
    # for i, constant in enumerate(module_constants):
    #     print(f"{i + 1}.", constant, constant._type_obj.__name__)
    # print("\n")

    # print("Flags")
    # for i, flag in enumerate(module_gflags):
    #     print(f"{i + 1}.", flag, flag._type_obj.__name__)
    # print("\n")

    for c in callbacks_found:
        # print("parsing callback")

        f = parse_function(gi_callback_to_py_type(c))
        if len(f._gi_callbacks) > 0:
            raise NotImplementedError("Nested callbacks not implemented")
        if f:
            module_used_callbacks.append(f)

    return Module(
        name=module_name,
        constant=module_constants,
        # enum=module_genums,
        # function=module_gflags,
        function=module_functions,
        used_callbacks=module_used_callbacks,
    ), unknown_module_map_types
    # print("Has Info")
    # for key, value in has_info.items():
    #     print(f"- {key}: {value}")
    #     print("\n")


def main():
    def asrepr(value: Any):
        if isinstance(value, (str, int, float)):
            return repr(value)
        return repr(value)

    # data, unknown_module_map_types = check_module(GObject)
    data, unknown_module_map_types = check_module(Gst)
    environment = jinja2.Environment()
    environment.filters["asrepr"] = asrepr
    output = environment.from_string(TEMPLATE)

    # print(
    #     output.render(
    #         constants=data.constant,
    #         # enums=data.enum,
    #         functions=data.function,
    #     )
    # )
    # print(module_map_types)
    # print(data.function)
    print("#" * 80)
    print("# callbacks")
    print("#" * 80)
    for f in data.used_callbacks:
        print(f)

    print("#" * 80)
    print("# functions")
    print("#" * 80)
    for f in data.function:
        print(f)

    for key, value in unknown_module_map_types.items():
        print(f"- {key}: \n{value}")
        print("\n")


if __name__ == "__main__":
    main()
