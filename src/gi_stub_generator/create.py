import inspect

from pydantic import BaseModel
from gi_stub_generator.parse import (
    parse_class,
    parse_constant,
    parse_enum,
    parse_function,
)
from gi_stub_generator.schema import (
    BuiltinFunctionSchema,
    ClassPropSchema,
    ClassSchema,
    EnumFieldSchema,
    EnumSchema,
    VariableSchema,
    FunctionArgumentSchema,
    FunctionSchema,
    Module,
)
from gi_stub_generator.utils import gi_callback_to_py_type, gi_type_to_py_type
import jinja2
from enum import Enum
from types import (
    FunctionType,
    ModuleType,
    BuiltinFunctionType,
    MethodDescriptorType,
    MethodType,
)
from typing import Any, Literal
import gi
import gi._gi as GI
from gi.repository import GObject, GIRepository
from .docstring import generate_doc_string, _generate_callable_info_doc

gi.require_version("Gst", "1.0")

GObject.child_watch_add
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


# TODO
# loop class
# inspect.getmembers(Gst, inspect.isclass)
# inspect.getmembers(Gst, inspect.isbuiltin)


def check_module(
    m: ModuleType,
):
    module_attributes = dir(m)
    module_name = m.__name__.split(".")[-1]
    module_constants: list[VariableSchema] = []
    module_functions: list[FunctionSchema] = []
    module_builtin_functions: list[BuiltinFunctionSchema] = []
    module_used_callbacks: list[FunctionSchema] = []
    module_enums: list[EnumFieldSchema] = []
    module_classes: list[ClassSchema] = []

    # map all module attributes to their types
    # has_info: dict[str, list[str]] = {}
    callbacks_found: list[GI.TypeInfo] = []
    unknown_module_map_types: dict[str, list[str]] = {}
    for attribute_name in module_attributes:
        if attribute_name.startswith("__"):
            continue

        attribute = getattr(m, attribute_name)
        attribute_type = type(attribute)

        #########################################################################
        # check for basic types if we are parsing GObject
        #########################################################################
        # these should be parsed as classes and not as their types
        if module_name == "GObject":
            # ['GBoxed', 'GEnum', 'GFlags', 'GInterface', 'GObject',
            # 'GObjectWeakRef', 'GPointer', 'GType', 'Warning']
            if attribute_name in (
                "GObject",
                "Object",
                "GType",
                "GFlags",
                "GEnum",
                "Warning",
                "GInterface",
                "GBoxed",
                "GObjectWeakRef",
            ):
                # TODO:
                # custom parsing for the default types

                # GEnum and GFlags need to add Enum to super and than can be parsed as class
                # -> (int, Enum)
                # GObject -> punta a GObject.Object
                # -> (Object)
                # Object
                # -> (object)
                # GInterface
                # -> (Protocol)
                # GType -> object ok mro()[1]
                # GObjectWeakRef -> object ok mro()[1]
                # GPointer -> object ok mro()[1]
                # Warning -> object ok mro()[1] (Warnign che è una Exception)
                # can be parsed as a class??
                continue

        #########################################################################
        # check if the attribute is a constant
        #########################################################################

        if c := parse_constant(
            parent=module_name,
            name=attribute_name,
            obj=attribute,
            # _gi_type=attribute_type,
        ):
            module_constants.append(c)
            continue

        #########################################################################
        # check if builtin function
        #########################################################################

        # builtin functions
        if attribute_type == FunctionType:
            # if std python function are found, parse via inspect
            # https://docs.python.org/3/library/inspect.html#inspect.getargvalues
            module_builtin_functions.append(
                BuiltinFunctionSchema(
                    name=attribute_name,
                    namespace=module_name,
                    signature=str(inspect.signature(attribute)),
                    docstring="TODO:",
                )
            )
            continue
        if attribute_type == BuiltinFunctionType:
            # Inspect do not work
            # TODO: is there a way to get the signature of a builtin function?
            module_builtin_functions.append(
                BuiltinFunctionSchema(
                    name=attribute_name,
                    namespace=module_name,
                    signature="(*args, **kwargs)",
                    docstring="cant inspect builtin functions",
                )
            )
            continue
            # i.e  GObject.add_emission_hook

        #########################################################################
        # check if the attribute is a function
        #########################################################################

        if isinstance(attribute, GI.VFuncInfo):
            # GIVFuncInfo
            # represents a virtual function.
            # A virtual function is a callable object that belongs to either a
            # GIObjectInfo or a GIInterfaceInfo.
            # TODO: could not find any example of this
            raise NotImplementedError("VFuncInfo not implemented")

        if f := parse_function(attribute):
            module_functions.append(f)
            # callbacks can be found as arguments of functions, save them to be parsed later
            callbacks_found.extend(f._gi_callbacks)
            continue

        #########################################################################
        # check if the attribute is an Enum/Flags
        #########################################################################

        if e := parse_enum(attribute):
            module_enums.append(e)
            continue

        #########################################################################
        # check if the attribute is a class (GObjectMeta, StructMeta and type)
        #########################################################################

        if parsed_class := parse_class(
            namespace=module_name,
            class_to_parse=attribute,
        ):
            module_classes.append(parsed_class)
            callbacks_found.extend(parsed_class._gi_callbacks)
            continue

        #########################################################################
        # unknown/not parsed types
        #########################################################################

        # check if the attribute is an enum
        attribute_type_name = attribute_type.__name__
        unknown_key = f"{attribute_type_name}[{attribute_type}]"
        if unknown_key in unknown_module_map_types:
            unknown_module_map_types[unknown_key].append(attribute_name)
        else:
            unknown_module_map_types[unknown_key] = [attribute_name]

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
        enum=module_enums,
        # function=module_gflags,
        function=module_functions,
        builtin_function=module_builtin_functions,
        used_callbacks=module_used_callbacks,
        classes=module_classes,
    ), unknown_module_map_types
    # print("Has Info")
    # for key, value in has_info.items():
    #     print(f"- {key}: {value}")
    #     print("\n")


def main():
    # data, unknown_module_map_types = check_module(GObject)
    data, unknown_module_map_types = check_module(Gst)
    environment = jinja2.Environment()
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
    print("# enum/flags")
    print("#" * 80)
    for f in data.enum:
        print(f)

    print("#" * 80)
    print("# constants")
    print("#" * 80)
    for f in data.constant:
        print(f)

    print("#" * 80)
    print("# callbacks")
    print("#" * 80)
    for f in data.used_callbacks:
        print(f)

    print("#" * 80)
    print("# builtin functions")
    print("#" * 80)
    for f in data.builtin_function:
        print(f)

    print("#" * 80)
    print("# functions")
    print("#" * 80)
    for f in data.function:
        print(f)

    print("#" * 80)
    print("# classes")
    print("#" * 80)
    for f in data.classes:
        print(f)

    print("#" * 80)
    print("# Unknown/Not parsed elements")
    print("#" * 80)
    for key, value in unknown_module_map_types.items():
        print(f"- {key}: \n{value}")
        print("\n")

    # print(data.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
