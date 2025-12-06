from __future__ import annotations


from gi_stub_gen.parser.builtin_function import parse_builtin_function
from gi_stub_gen.parser.constant import parse_constant
from gi_stub_gen.parser.enum import parse_enum
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.gir import ModuleDocs
from gi_stub_gen.parser.class_ import (
    parse_class,
)

import logging
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

from gi_stub_gen.utils import (
    catch_gi_deprecation_warnings,
    sanitize_module_name,
)
from types import ModuleType

import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject, GIRepository

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi_stub_gen.schema.module import ModuleSchema
    from gi_stub_gen.schema.alias import AliasSchema
    from gi_stub_gen.schema.class_ import ClassSchema
    from gi_stub_gen.schema.constant import VariableSchema
    from gi_stub_gen.schema.enum import EnumSchema
    from gi_stub_gen.schema.function import (
        BuiltinFunctionSchema,
        FunctionSchema,
        CallbackSchema,
    )


logger = logging.getLogger(__name__)


def parse_module(
    m: ModuleType,
    gir_f_docs: ModuleDocs,
    debug: bool = False,
) -> tuple[ModuleSchema, dict[str, list[str]]]:
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

    callbacks_found: list[CallbackSchema] = []
    """callback can be found in module functions or in class methods """

    unknown_module_map_types: dict[str, list[str]] = {}

    module_aliases: list[AliasSchema] = []
    """Aliases found in the module, parsed as AliasSchema objects"""

    # processed_classes = {}

    logger.info("#" * 80)
    logger.info(
        f"Parsing module {module_name} with {len(module_attributes)} attributes"
    )
    logger.info("#" * 80)

    # retrieve console from the rich logging handler
    logging_console = logger.root.handlers[0].console  # type: ignore
    progress_columns = [
        SpinnerColumn(),
        TextColumn(f"[green][progress.description]Parsing module {module_name}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TextColumn("[progress.description]{task.description}"),
    ]

    from gi_stub_gen.schema.alias import AliasSchema

    with Progress(
        *progress_columns,
        console=logging_console,
        disable=debug,
    ) as progress:
        task = progress.add_task("[red]Processing...", total=len(module_attributes))

        for attribute_idx, attribute_name in enumerate(module_attributes):
            progress.update(
                task,
                description=f"[green]{module_name}.{attribute_name}...",
                advance=1,
            )

            if attribute_name.startswith("__"):
                logger.debug(
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
                    sanitized_module_name = sanitize_module_name(
                        str(attribute.__module__)
                    )

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

                # logger.debug(
                #     f"\t[ALIAS][SAME_NS] {module_name}.{attribute_name} -> {attribute.__name__}\n"
                # )
                continue

            actual_attribute_module = (
                (str(attribute.__module__))
                if hasattr(attribute, "__module__")
                else None
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

                # logger.debug(
                #     f"\t[ALIAS][OTHER_NS] skipping {module_name}.{attribute_name} -> {attribute.__module__}.{attribute_name}\n"
                # )
                continue

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
                # logger.debug(f"\t[CONSTANT] {attribute_name}\n")
                continue

            #########################################################################
            # check if builtin function
            #########################################################################

            if f := parse_builtin_function(
                attribute,
                module_name,
            ):
                module_builtin_functions.append(f)
                continue
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

                # logger.debug(f"\tfound [FUNCTION] {attribute_name}\n")
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
                # logger.debug(f"\t[ENUM] {attribute_name}\n")
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
                # logger.debug(f"\t[CLASS] {attribute_name}\n")
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

            # logger.warning(f"\t[??][UNKNOWN] {module_name}.{attribute_name}")

    # end for attribute in module_attributes
    #########################################################################

    # just filter only the callbacks used in the module
    module_callbacks: dict[str, CallbackSchema] = {}
    for cb in callbacks_found:
        assert cb.function.is_callback, "Expected a callback function schema"

        if cb.name not in module_callbacks:
            module_callbacks[cb.name] = cb
        else:
            # check if the existing callback is the same as the new one
            existing_cb = module_callbacks[cb.name]
            assert existing_cb.function == cb.function, (
                f"Expected same function schema for the same callback name but {cb.function} != {existing_cb.function}"
            )
            assert existing_cb.originated_from is not None, (
                "Expected originated_from to be not None"
            )
            assert cb.originated_from is not None, (
                "Expected originated_from to be not None"
            )
            # we merge
            existing_cb.originated_from.update(cb.originated_from)

    from gi_stub_gen.schema.module import ModuleSchema

    return ModuleSchema(
        name=module_name,
        constant=module_constants,
        enum=module_enums,
        function=module_functions,
        builtin_function=module_builtin_functions,
        callbacks=[v for v in module_callbacks.values()],
        classes=module_classes,
        aliases=module_aliases,
    ), unknown_module_map_types
