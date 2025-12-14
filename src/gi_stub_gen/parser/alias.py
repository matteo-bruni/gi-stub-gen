from typing import Any
from gi_stub_gen.gi_utils import catch_gi_deprecation_warnings
from gi_stub_gen.overrides.class_.GObject import GFLAG_SCHEMA
from gi_stub_gen.overrides.class_.GObject import GENUM_SCHEMA
from gi_stub_gen.schema.alias import AliasSchema
from gi_stub_gen.schema.class_ import ClassSchema
from gi_stub_gen.utils import sanitize_gi_module_name


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
    actual_attribute_name = (
        attribute.__name__.split(".")[-1]
        if hasattr(attribute, "__name__")
        else attribute_name
    )
    ########################################################################
    # check for aliases in same module
    ########################################################################

    if actual_attribute_name != attribute_name:
        # we found an alias, ie GObject.Object is an alias for GObject.GObject

        line_comment = None
        if hasattr(attribute, "__module__"):
            sanitized_module_name = sanitize_gi_module_name(str(attribute.__module__))
            if str(sanitized_module_name).startswith(("gi.", "_thread")):
                line_comment = "type: ignore"
        # else:
        #     # if no module is present, we assume it is in the same module
        #     # these are most likely overrides
        #     sanitized_module_name = module_name
        #     line_comment = "type: ignore  # no __module__ attribute"

        target = sanitize_gi_module_name(attribute.__name__)

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

    actual_attribute_module = (
        (str(attribute.__module__)) if hasattr(attribute, "__module__") else None
    )

    if (
        actual_attribute_module
        and module_name.split(".")[-1].lower()
        != actual_attribute_module.split(".")[-1].lower()
    ):
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

        return AliasSchema(
            name=attribute_name,
            target_namespace=sanitized_module_name,
            target_name=actual_attribute_name,
            deprecation_warning=w,
            line_comment="type: ignore"
            if str(attribute.__module__).startswith(("gi.", "_thread"))
            else None,
            alias_to="other_module",
        )

    # not an alias
    return None
