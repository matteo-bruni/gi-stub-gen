from __future__ import annotations


from gi_stub_gen.gir_manager import GIRDocs
from gi_stub_gen.parser.alias import parse_alias
from gi_stub_gen.parser.python_function import parse_python_function
from gi_stub_gen.parser.constant import parse_constant
from gi_stub_gen.parser.enum import parse_enum
from gi_stub_gen.parser.function import parse_function
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

from types import ModuleType
import gi._gi as GI  # pyright: ignore[reportMissingImports]

from typing import TYPE_CHECKING

from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema

if TYPE_CHECKING:
    from gi_stub_gen.schema.module import ModuleSchema
    from gi_stub_gen.schema.alias import AliasSchema
    from gi_stub_gen.schema.class_ import ClassSchema
    from gi_stub_gen.schema.constant import VariableSchema
    from gi_stub_gen.schema.enum import EnumSchema
    from gi_stub_gen.schema.function import (
        FunctionSchema,
        CallbackSchema,
    )


logger = logging.getLogger(__name__)


def parse_module(
    m: ModuleType,
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
    logger.info(f"Parsing module {module_name} with {len(module_attributes)} attributes")
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
    from gi_stub_gen.schema.class_ import ClassSchema

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
                logger.debug(f"\t[SKIP][{module_name}] skipping dunder attribute {attribute_name}")
                continue

            attribute = getattr(m, attribute_name)
            attribute_type = type(attribute)

            # ########################################################################
            # # check for aliases in same or other modules
            # ########################################################################
            if a := parse_alias(
                module_name=module_name,
                attribute_name=attribute_name,
                attribute=attribute,
            ):
                if isinstance(a, AliasSchema):
                    module_aliases.append(a)
                elif isinstance(a, ClassSchema):
                    # this is a manual override for GEnum/GFlags
                    # that are inserted as classes
                    # GEnum and GFlags are normally alias to gi._gi.GEnum and gi._gi.GFlags
                    # but we fake them as real classes in the GObject module
                    module_classes.append(a)
                else:
                    raise ValueError(f"Expected AliasSchema or ClassSchema but got {type(a)}")

                continue
            #########################################################################
            # check if the attribute is a constant
            #########################################################################
            if c := parse_constant(
                module_name=module_name,
                name=attribute_name,
                obj=attribute,
                docstring=GIRDocs().get_constant_docs(attribute_name),
            ):
                module_constants.append(c)
                # logger.debug(f"\t[CONSTANT] {attribute_name}\n")
                continue

            #########################################################################
            # check if builtin function
            #########################################################################
            if f := parse_python_function(
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

            # docstring.get(attribute.get_name(), None)
            if f := parse_function(
                attribute,
                docstring=GIRDocs().get_function_docstring(attribute_name),
            ):
                module_functions.append(f)
                # callbacks can be found as arguments of functions,
                # save them to be parsed later
                callbacks_found.extend(f._gi_callbacks)
                continue

            #########################################################################
            # check if the attribute is an Enum/Flags
            #########################################################################
            if e := parse_enum(
                attribute,
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
                module_name=module_name,
                class_to_parse=attribute,
            )
            if class_schema:
                module_classes.append(class_schema)
                callbacks_found.extend(class_callbacks_found)
                continue

            #########################################################################
            # unknown/not parsed types
            #########################################################################
            # if we reach this point, we could not parse the attribute
            attribute_type_name = attribute_type.__name__
            unknown_key = f"{attribute_type_name}"  # [{attribute_type}]"
            if unknown_key in unknown_module_map_types:
                unknown_module_map_types[unknown_key].append(attribute_name)
            else:
                unknown_module_map_types[unknown_key] = [attribute_name]

    # end for attribute in module_attributes
    #########################################################################

    # add override callbacks
    from gi_stub_gen.overrides import CALLBACK_OVERRIDES

    for override in CALLBACK_OVERRIDES.get(module_name, {}).values():
        if override.name not in [cb.name for cb in callbacks_found]:
            callbacks_found.append(override)

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
                f"Expected same function schema for the same callback name but"
                f" \n{cb.function=}\n != \n{existing_cb.function=}\n"
                f"\n{cb.originated_from=}\n != \n{existing_cb.originated_from=}\n"
            )
            assert existing_cb.originated_from is not None, "Expected originated_from to be not None"
            assert cb.originated_from is not None, "Expected originated_from to be not None"
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
