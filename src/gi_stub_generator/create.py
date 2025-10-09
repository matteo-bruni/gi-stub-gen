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
    AliasSchema,
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
import logging

# from gi_stub_generator.template import TEMPLATE
from gi_stub_generator.utils import (
    catch_gi_deprecation_warnings,
    # get_symbol_name,
    gi_callback_to_py_type,
    # gi_type_to_py_type,
    sanitize_module_name,
)
from types import (
    FunctionType,
    ModuleType,
    BuiltinFunctionType,
)

import gi._gi as GI  # pyright: ignore[reportMissingImports]
# from gi.repository import GObject, GIRepository

logger = logging.getLogger(__name__)


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
    module_name = m.__name__
    # module_name = m.__name__.split(".")[-1]
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

    module_aliases: list[AliasSchema] = []
    """Aliases found in the module, parsed as AliasSchema objects"""

    # processed_classes = {}

    # map all module attributes to their types
    for attribute_idx, attribute_name in enumerate(module_attributes):
        logger.debug(
            f"[{module_name}] ({attribute_idx + 1}/{len(module_attributes)}) checking {module_name}.{attribute_name}"
        )

        if attribute_name.startswith("__"):
            logger.warning(
                f"\t[SKIP][{module_name}] skipping dunder attribute {attribute_name}"
            )
            continue
        # if attribute_idx > 4:
        #     exit()
        attribute_deprecation_warnings: str | None = None

        attribute = getattr(m, attribute_name)
        attribute_type = type(attribute)

        ########################################################################
        # check for aliases in same or other modules
        ########################################################################
        # alias in the same module
        actual_attribute_name = (
            attribute.__name__.split(".")[-1]
            if hasattr(attribute, "__name__")
            else attribute_name
        )
        if actual_attribute_name != attribute_name:
            # we found an alias, ie GObject.Object is an alias for GObject.GObject

            line_comment = None
            if hasattr(attribute, "__module__"):
                sanitized_module_name = sanitize_module_name(str(attribute.__module__))

                if str(attribute.__module__).startswith(("gi.", "_thread")):
                    line_comment = "# type: ignore"
            else:
                sanitized_module_name = module_name

            module_aliases.append(
                AliasSchema(
                    name=attribute_name,
                    target_name=attribute.__name__,
                    target_namespace=sanitized_module_name,
                    deprecation_warning=catch_gi_deprecation_warnings(
                        module_name,
                        attribute_name,
                    ),
                    line_comment=line_comment,
                )
            )

            logger.debug(
                f"\t[ALIAS][SAME_NS] {module_name}.{attribute_name} -> {attribute.__name__}\n"
            )
            continue

        actual_attribute_module = (
            (str(attribute.__module__)) if hasattr(attribute, "__module__") else None
        )

        # alias to another module
        if (
            actual_attribute_module
            and module_name.split(".")[-1].lower()
            != actual_attribute_module.split(".")[-1].lower()
        ):
            # warnings are caught on the expected module and attribute
            w = catch_gi_deprecation_warnings(module_name, attribute_name)

            sanitized_module_name = sanitized_module_name = sanitize_module_name(
                str(attribute.__module__)
            )

            if sanitized_module_name == "gi" or sanitized_module_name == "builtins":
                # many object have a gi. module (i.e. gi._gi.RegisteredTypeInfo -> gi.RegisteredTypeInfo)
                # but any gi.<XX> in reality does not exist
                module_aliases.append(
                    AliasSchema(
                        name=attribute_name,
                        target_namespace=None,
                        target_name=None,
                        deprecation_warning=w,
                        line_comment="# alias to gi.<XX> module or builtins that does not exist",
                    )
                )
            else:
                module_aliases.append(
                    AliasSchema(
                        name=attribute_name,
                        target_namespace=sanitized_module_name,
                        target_name=actual_attribute_name,
                        deprecation_warning=w,
                        line_comment="# type: ignore"
                        if str(attribute.__module__).startswith(("gi.", "_thread"))
                        else None,
                    )
                )

            logger.debug(
                f"\t[ALIAS][OTHER_NS] skipping {module_name}.{attribute_name} -> {attribute.__module__}.{attribute_name}\n"
            )
            continue

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
            deprecation_warnings=catch_gi_deprecation_warnings(
                module_name, attribute_name
            ),
        ):
            module_constants.append(c)
            logger.debug(f"\t[CONSTANT] {attribute_name}\n")
            continue

        #########################################################################
        # check if builtin function
        #########################################################################

        # builtin functions
        if attribute_type == FunctionType:
            # if std python function are found, parse via inspect
            # https://docs.python.org/3/library/inspect.html#inspect.getargvalues

            # breakpoint()
            module_builtin_functions.append(
                BuiltinFunctionSchema(
                    name=attribute_name,
                    namespace=module_name,
                    signature=str(inspect.signature(attribute)),
                    docstring=inspect.getdoc(attribute) or "No docstring",
                    return_repr="None"
                    if inspect.signature(attribute).return_annotation == inspect._empty
                    else str(inspect.signature(attribute).return_annotation),
                    params=[
                        f"{p}: {v}"
                        for p, v in inspect.signature(attribute).parameters.items()
                    ],
                )
            )
            logger.debug(f"\t[FUNCTION][FunctionType] {attribute_name}\n")
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
                    return_repr="Unknown",
                    params=["*args, **kwargs"],
                )
            )
            logger.debug(f"\t[FUNCTION][BuiltinFunctionType] {attribute_name}\n")
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
            deprecation_warnings=catch_gi_deprecation_warnings(
                module_name, attribute_name
            ),
        ):
            module_functions.append(f)
            # callbacks can be found as arguments of functions, save them to be parsed later
            callbacks_found.extend(f._gi_callbacks)

            logger.debug(f"\t[FUNCTION] {attribute_name}\n")
            continue

        #########################################################################
        # check if the attribute is an Enum/Flags
        #########################################################################

        if e := parse_enum(
            attribute,
            gir_f_docs.enums,
            attribute_deprecation_warnings,
        ):
            # if e.name in gir_f_docs["enums"]:
            #    e.docstring = gir_f_docs["enums"][e.name]
            module_enums.append(e)
            logger.debug(f"\t[ENUM] {attribute_name}\n")
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
            # if f"{attribute}" in processed_classes:
            #     logger.warning(
            #         f"[DUPLICATE]"
            #         f"<{attribute.__module__}.{attribute.__name__}> "
            #         f"vs "
            #         f"<{processed_classes[f'{attribute}'].__module__}.{processed_classes[f'{attribute}'].__name__}> "
            #         f"Class {class_schema.name} already exists in the module {module_name}. "
            #     )
            # else:
            #     processed_classes[f"{attribute}"] = attribute

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
            logger.debug(f"\t[CLASS] {attribute_name}\n")
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

        logger.warning(f"\t[??][UNKNOWN] {attribute_name}\n")

    # just filter only the callbacks used in the module
    module_used_callbacks: list[FunctionSchema] = []
    for c in callbacks_found:
        f = parse_function(gi_callback_to_py_type(c), gir_f_docs.functions, None)
        if f and len(f._gi_callbacks) > 0:
            raise NotImplementedError("Nested callbacks not implemented")
        if f:
            module_used_callbacks.append(f)

    # log the unknown types
    if len(unknown_module_map_types) > 0:
        logger.warning("" + "#" * 80)
        logger.warning(f"[{module_name}] Unknown types found in the module:")
        for unknown_type, attributes in unknown_module_map_types.items():
            logger.warning(f"- {unknown_type}: {attributes}")

    else:
        logger.info(f"[{module_name}] No unknown types found in the module")

    return Module(
        name=module_name,
        constant=module_constants,
        enum=module_enums,
        # function=module_gflags,
        function=module_functions,
        builtin_function=module_builtin_functions,
        used_callbacks=module_used_callbacks,
        classes=module_classes,
        aliases=module_aliases,
    ), unknown_module_map_types
    # print("Has Info")
    # for key, value in has_info.items():
    #     print(f"- {key}: {value}")
    #     print("\n")
