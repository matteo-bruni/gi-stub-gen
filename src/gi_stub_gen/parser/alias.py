from types import ModuleType
from typing import Any
from gi_stub_gen.utils.gi_utils import catch_gi_deprecation_warnings
from gi_stub_gen.overrides.class_.GObject.GFlag import GFLAG_SCHEMA
from gi_stub_gen.overrides.class_.GObject.GEnum import GENUM_SCHEMA
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.schema.alias import AliasSchema
from gi_stub_gen.schema.class_ import ClassSchema
from gi_stub_gen.utils.utils import sanitize_gi_module_name


def parse_alias(
    module_name: str,  # name of the module where the attribute is located
    attribute_name: str,  # name of the attribute
    attribute: Any,  # object to be parsed
) -> AliasSchema | ClassSchema | None:
    """
    Parse an attribute and return an AliasSchema if it is an alias.
    Can be an alias in the same module or to another module.
    Special handling for GEnum and GFlags to return manual override schema, which is instead a ClassSchema.

    Args:
        module_name (str): name of the module where the attribute is located
        attribute_name (str): name of the attribute
        attribute (Any): object to be parsed
    Returns:
        AliasSchema | ClassSchema | None: parsed alias schema or None if the attribute is not an alias, ClassSchema for GObject.GEnum/GFlags

    """

    # alias in the same module
    actual_attribute_name = attribute.__name__.split(".")[-1] if hasattr(attribute, "__name__") else attribute_name
    actual_attribute_module = (str(attribute.__module__)) if hasattr(attribute, "__module__") else None

    ########################################################################
    # check for aliases in same module
    ########################################################################

    actual_attribute_name_is_different = actual_attribute_name != attribute_name
    actual_attribute_module_is_different = (
        actual_attribute_module and module_name.split(".")[-1].lower() != actual_attribute_module.split(".")[-1].lower()
    )

    if actual_attribute_name_is_different and not actual_attribute_module_is_different:
        # we found an alias, ie GObject.Object is an alias for GObject.GObject

        line_comment = None
        target = sanitize_gi_module_name(attribute.__name__)

        if hasattr(attribute, "__module__"):
            sanitized_module_name = sanitize_gi_module_name(str(attribute.__module__))
            # Add type: ignore for aliases pointing to private gi modules,
            # but NOT when the target will be present in the same generated stub
            # (e.g., property = Property where Property is added via manual override)
            if str(sanitized_module_name).startswith(("gi.", "_thread")):
                # Property is added to GObject.pyi via CLASS_PROPERTY override,
                # so "property = Property" doesn't need type: ignore
                if not (sanitized_module_name == "gi._propertyhelper" and actual_attribute_name == "Property"):
                    line_comment = "type: ignore"

        if type(attribute) is ModuleType:
            if target.startswith("gi._"):
                line_comment = "type: ignore alias to private gi._ module"

        # _overrides are in the same module
        if target == sanitize_gi_module_name(module_name):
            target = "..."
            line_comment = f"this very module {target}"

        return AliasSchema(
            name=attribute_name,
            target_name=target,
            target_namespace=None,  # we assume same module so no need to specify
            deprecation_warning=catch_gi_deprecation_warnings(
                module_name,
                attribute_name,
            ),
            line_comment=line_comment,
            alias_to="same_module",
        )

    ########################################################################
    # check for aliases to other module
    ########################################################################

    # if actual_attribute_module and module_name.split(".")[-1].lower() != actual_attribute_module.split(".")[-1].lower():
    if actual_attribute_module_is_different:
        sanitized_module_name = sanitize_gi_module_name(str(attribute.__module__))
        #######################################################################
        # manual override just for GEnum and Flags.
        # they are in GObject.GEnum / GObject.GFlags
        # but are aliases to gi._gi.GEnum / gi._gi.GFlags (i.e the target alias)
        # the one present in gi._gi do not export all the value_nick and value_name
        # that are addedd at runtime. so we fake the schema here
        #######################################################################
        if sanitized_module_name == "gi._gi" and attribute_name == "GEnum":
            return GENUM_SCHEMA
        elif sanitized_module_name == "gi._gi" and attribute_name == "GFlags":
            return GFLAG_SCHEMA
        elif sanitized_module_name == "gi._propertyhelper" and attribute_name == "Property":
            # will be added later at the end of module parsing via custom overrides
            return None

        # warnings are caught on the expected module and attribute
        w = catch_gi_deprecation_warnings(
            module_name,
            attribute_name,
        )

        # if sanitized_module_name == "gi" or sanitized_module_name == "builtins":
        if sanitized_module_name == "builtins":
            # many object have a gi. module (i.e. gi._gi.RegisteredTypeInfo -> gi.RegisteredTypeInfo)
            # but any gi.<XX> in reality does not exist
            return AliasSchema(
                name=attribute_name,
                target_namespace=None,
                target_name=None,
                deprecation_warning=w,
                line_comment="alias to gi.<XX> module or builtins that does not exist",
                alias_to="other_module",
            )
        # TODO: decide what to do with gi module aliases
        # if we are in gi._gi, the TypeInfo is here but it belives to be in gi.TypeInfo
        if sanitized_module_name == "gi":
            return None

        # skip the overrides aliases
        if sanitized_module_name == "gi.overrides":
            return None

        if sanitized_module_name == "gi._gi":
            # we try to parse the class from gi._gi module
            # and fake it to being in this module
            class_schema, class_callbacks_found = parse_class(
                module_name="gi._gi",
                class_to_parse=attribute,
            )
            if class_schema:
                extra_docstring = (
                    f"Alias to gi._gi.{attribute_name}. May Be incomplete since gi._gi is a private module."
                )
                class_schema.docstring = (
                    f"{extra_docstring}\n\n{class_schema.docstring}" if class_schema.docstring else extra_docstring
                )
                return class_schema
            # breakpoint()

        return AliasSchema(
            name=attribute_name,
            target_namespace=sanitized_module_name,
            target_name=actual_attribute_name,
            deprecation_warning=w,
            line_comment="type: ignore " if sanitized_module_name.startswith(("gi.", "_thread")) else None,
            alias_to="other_module",
        )

    # not an alias
    return None
