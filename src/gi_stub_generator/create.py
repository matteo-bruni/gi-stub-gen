import inspect
from pathlib import Path

from pydantic import BaseModel
from gi_stub_generator.gir_parser import ModuleDocs, gir_docs
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

# from gi_stub_generator.template import TEMPLATE
from gi_stub_generator.utils import gi_callback_to_py_type, gi_type_to_py_type
from types import (
    FunctionType,
    ModuleType,
    BuiltinFunctionType,
)

import gi._gi as GI  # pyright: ignore[reportMissingImports]
# from gi.repository import GObject, GIRepository


def check_module(
    m: ModuleType,
    gir_f_docs: ModuleDocs,
) -> tuple[Module, dict[str, list[str]]]:
    """
    Check the module and parse its attributes into a Module object.

    Args:
        m (ModuleType): The module to check.
        gir_f_docs (ModuleDocs): The documentation for the module (parsed from gir files).

    Returns:
        tuple[Module, dict[str, list[str]]]: A tuple containing the parsed Module object and a dictionary of unknown types.

    """
    module_attributes = dir(m)
    module_name = m.__name__.split(".")[-1]
    module_constants: list[VariableSchema] = []
    """Constants found in the module, parsed as VariableSchema objects"""

    module_functions: list[FunctionSchema] = []
    """Functions found in the module, parsed as FunctionSchema objects"""

    module_builtin_functions: list[BuiltinFunctionSchema] = []
    """Builtin functions found in the module, parsed as BuiltinFunctionSchema objects"""

    module_enums: list[EnumSchema] = []
    """Enums found in the module, parsed as EnumSchema objects"""

    module_classes: list[ClassSchema] = []
    """Classes found in the module, parsed as ClassSchema objects"""

    callbacks_found: list[GI.TypeInfo] = []
    """callback can be found in module functions or in class methods """

    unknown_module_map_types: dict[str, list[str]] = {}

    import warnings
    import gi

    # map all module attributes to their types
    for attribute_idx, attribute_name in enumerate(module_attributes):
        if attribute_name.startswith("__"):
            continue

        attribute_deprecation_warnings: str | None = None
        # check if the attribute is deprecated
        # with warnings.catch_warnings(record=True) as captured_warnings:
        #     warnings.simplefilter("always", category=gi.PyGIDeprecationWarning)  # type: ignore

        #     # actually get the attribute
        #     # only when doing this we can catch deprecation warnings
        #     attribute = getattr(m, attribute_name)
        #     attribute_type = type(attribute)

        #     for warning in captured_warnings:
        #         if issubclass(warning.category, gi.PyGIDeprecationWarning):  # type: ignore
        #             attribute_deprecation_warnings = (
        #                 f"{attribute_deprecation_warnings}. {warning.message}"
        #                 if attribute_deprecation_warnings
        #                 else str(warning.message)
        #             )

        attribute = getattr(m, attribute_name)
        attribute_type = type(attribute)
        #########################################################################
        # check for basic types if we are parsing GObject
        #########################################################################
        # TODO:
        # these should be parsed as classes and not as their types
        # if module_name == "GObject":
        #     # ['GBoxed', 'GEnum', 'GFlags', 'GInterface', 'GObject',
        #     # 'GObjectWeakRef', 'GPointer', 'GType', 'Warning']
        #     if attribute_name in (
        #         "GObject",
        #         "Object",
        #         "GType",
        #         "GFlags",
        #         "GEnum",
        #         "Warning",
        #         "GInterface",
        #         "GBoxed",
        #         "GObjectWeakRef",
        #     ):
        #         # TODO:
        #         # custom parsing for the default types
        #         # GEnum and GFlags need to add Enum to super and than can be parsed as class
        #         # -> (int, Enum)
        #         # GObject -> punta a GObject.Object
        #         # -> (Object)
        #         # Object
        #         # -> (object)
        #         # GInterface
        #         # -> (Protocol)
        #         # GType -> object ok mro()[1]
        #         # GObjectWeakRef -> object ok mro()[1]
        #         # GPointer -> object ok mro()[1]
        #         # Warning -> object ok mro()[1] (Warnign che è una Exception)
        #         # can be parsed as a class??
        #         continue

        #########################################################################
        # check if the attribute is a constant
        #########################################################################

        if c := parse_constant(
            parent=module_name,
            name=attribute_name,
            obj=attribute,
            docstring=gir_f_docs.constants.get(attribute_name, None),
            # deprecation_warnings=attribute_deprecation_warnings,
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
            # TODO: could not find any example of this ??
            raise NotImplementedError("VFuncInfo not implemented, open an issue?")

        if f := parse_function(
            attribute,
            gir_f_docs.functions,
            attribute_deprecation_warnings,
        ):
            module_functions.append(f)
            # callbacks can be found as arguments of functions, save them to be parsed later
            callbacks_found.extend(f._gi_callbacks)
            # if f.name == "meta_api_type_register":
            #     breakpoint()
            continue

        #########################################################################
        # check if the attribute is an Enum/Flags
        #########################################################################
        # if attribute_name == "GType":
        #     breakpoint()
        if e := parse_enum(
            attribute,
            gir_f_docs.enums,
            attribute_deprecation_warnings,
        ):
            # if e.name in gir_f_docs["enums"]:
            #    e.docstring = gir_f_docs["enums"][e.name]
            module_enums.append(e)
            continue

        #########################################################################
        # check if the attribute is a class (GObjectMeta, StructMeta and type)
        #########################################################################
        class_schema, class_callbacks_found = parse_class(
            namespace=module_name,
            class_to_parse=attribute,
            module_docs=gir_f_docs,
            deprecation_warnings=attribute_deprecation_warnings,
        )
        if class_schema:
            module_classes.append(class_schema)
            callbacks_found.extend(class_callbacks_found)
            # if class_schema.name == "Error":
            #     print(attribute_idx, "Found Error class", attribute_name)
            # if class_schema.name in unique_classes:
            #     raise ValueError(
            #         f"Class {class_schema.name} already exists in the module {module_name}. "
            #         "This is likely a bug in the gir parser, please open an issue."
            #     )
            # unique_classes.add(class_schema.name)
            continue

        #########################################################################
        # unknown/not parsed types
        #########################################################################
        attribute_type_name = attribute_type.__name__
        unknown_key = f"{attribute_type_name}[{attribute_type}]"
        if unknown_key in unknown_module_map_types:
            unknown_module_map_types[unknown_key].append(attribute_name)
        else:
            unknown_module_map_types[unknown_key] = [attribute_name]

    # just filter only the callbacks used in the module
    module_used_callbacks: list[FunctionSchema] = []
    for c in callbacks_found:
        f = parse_function(gi_callback_to_py_type(c), gir_f_docs.functions, None)
        if f and len(f._gi_callbacks) > 0:
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


# def main():
#     # module = GstVideo
#     module = Gst
#     docs = gir_docs(Path("/usr/share/gir-1.0/Gst-1.0.gir"))

#     # obtain docs from gir if available
#     # module = GObject
#     # docs = gir_docs(Path("/usr/share/gir-1.0/GObject-2.0.gir"))

#     data, unknown_module_map_types = check_module(module, docs)
#     # data, unknown_module_map_types = check_module(Gst)
#     environment = jinja2.Environment()
#     output = environment.from_string(TEMPLATE)

#     print(
#         output.render(
#             module=module.__name__.split(".")[-1],
#             constants=data.constant,
#             enums=data.enum,
#             functions=data.function,
#             classes=data.classes,
#         )
#     )

#     print("#" * 80)
#     print("# Unknown/Not parsed elements")
#     print("#" * 80)
#     for key, value in unknown_module_map_types.items():
#         print(f"- {key=}: \n{value=}")
#         print("\n")
#     return

#     print("#" * 80)
#     print("# enum/flags")
#     print("#" * 80)
#     for f in data.enum:
#         print(f)

#     print("#" * 80)
#     print("# constants")
#     print("#" * 80)
#     for f in data.constant:
#         print(f)

#     print("#" * 80)
#     print("# callbacks")
#     print("#" * 80)
#     for f in data.used_callbacks:
#         print(f)

#     print("#" * 80)
#     print("# builtin functions")
#     print("#" * 80)
#     for f in data.builtin_function:
#         print(f)

#     print("#" * 80)
#     print("# functions")
#     print("#" * 80)
#     for f in data.function:
#         print(f)

#     print("#" * 80)
#     print("# classes")
#     print("#" * 80)
#     for f in data.classes:
#         print(f)

#     print("#" * 80)
#     print("# Unknown/Not parsed elements")
#     print("#" * 80)
#     for key, value in unknown_module_map_types.items():
#         print(f"- {key}: \n{value}")
#         print("\n")

#     # print(data.model_dump_json(indent=2))


# if __name__ == "__main__":
#     main()
