from __future__ import annotations

import datetime
import logging
from importlib.metadata import version, PackageNotFoundError

from gi_stub_gen.manager import TemplateManager
from gi_stub_gen.utils import get_gi_module_from_name, sanitize_gi_module_name

from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.alias import AliasSchema
from gi_stub_gen.schema.constant import VariableSchema
from gi_stub_gen.schema.function import (
    BuiltinFunctionSchema,
    FunctionSchema,
    CallbackSchema,
)
from gi_stub_gen.schema.class_ import ClassSchema
from gi_stub_gen.schema.enum import EnumSchema


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


def get_gi_stubgen_version():
    package_name = "gi-stub-gen"

    try:
        pkg_version = version(package_name)
    except PackageNotFoundError:
        pkg_version = "dev-local"
    return pkg_version


class ModuleSchema(BaseSchema):
    name: str
    classes: list[ClassSchema]
    constant: list[VariableSchema]
    enum: list[EnumSchema]
    function: list[FunctionSchema]
    builtin_function: list[BuiltinFunctionSchema]
    callbacks: list[CallbackSchema]
    aliases: list[AliasSchema]

    def collect_imports(self) -> tuple[set[str], set[str]]:
        sane_module_name = sanitize_gi_module_name(self.name)

        gi_imports: set[str] = set()
        for c in self.classes:
            gi_imports.update(c.required_gi_imports)
        for f in self.function:
            gi_imports.update(f.required_gi_imports)
        for a in self.aliases:
            if a.target_namespace is not None:
                gi_imports.add(a.target_namespace)

        # remove current module name from imports
        if sane_module_name in gi_imports:
            gi_imports.remove(sane_module_name)

        # some non gi.repository imports can be slipped in the set
        # we just try to import and remove the ones that fail
        valid_gi_imports: set[str] = set()
        not_gi_imports: set[str] = set()
        for gi_import in gi_imports:
            try:
                get_gi_module_from_name(gi_import, None)
                valid_gi_imports.add(gi_import)
            except ImportError:
                logger.warning(
                    f"Invalid gi.repository import {gi_import} in module {self.name}"
                )
                if not gi_import.startswith("GI."):
                    not_gi_imports.add(gi_import)

        # logger.error(
        #     f"Module {self.name} - Removed invalid gi.repository imports: {not_gi_imports}"
        # )

        return valid_gi_imports, not_gi_imports

    def to_pyi(
        self,
        extra_gi_repository_import: list[str],
        unknowns: dict[str, list[str]],
        debug=False,
    ) -> str:
        sane_module_name = sanitize_gi_module_name(self.name)

        # add all the gi.repository imports needed
        gi_imports, not_gi_imports = self.collect_imports()

        # this is needed to set the module name in the template manager
        TemplateManager.set_debug(debug=debug)
        TemplateManager.set_module_name(sane_module_name)

        return TemplateManager.render_master(
            template_name="module.pyi.jinja",
            gi_stub_gen_version=get_gi_stubgen_version(),
            generation_date=datetime.datetime.now().strftime("%Y-%m-%d"),
            classes=self.classes,
            enums=self.enum,
            constants=self.constant,
            functions=self.function,
            builtin_functions=self.builtin_function,
            extra_gi_repository_import=gi_imports,
            extra_imports=not_gi_imports,
            unknowns=unknowns,
            aliases=self.aliases,
            callbacks=self.callbacks,
        )

        """
        Return the module as a pyi file
        """
        import jinja2
        from gi_stub_gen.template import TEMPLATE

        environment = jinja2.Environment()
        output_template = environment.from_string(TEMPLATE)
        sanitized_module_name = sanitize_gi_module_name(self.name)

        # print(self.callbacks)
        return output_template.render(
            module=sanitized_module_name,
            # module=module.__name__.split(".")[-1],
            constants=self.constant,
            enums=self.enum,
            functions=self.function,
            builtin_function=self.builtin_function,
            classes=self.classes,
            debug=debug,
            aliases=self.aliases,
            callbacks=self.callbacks,
            extra_gi_repository_import=extra_gi_repository_import,
            unknowns=unknowns,
        )
