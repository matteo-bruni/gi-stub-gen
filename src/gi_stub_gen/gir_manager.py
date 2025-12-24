from __future__ import annotations
import logging
from pathlib import Path

from gi_stub_gen.parser.gir import ModuleDocs, parse_gir_docs

# from gi_stub_gen.parser.gir import ModuleDocs, parse_gir_docs
from gi_stub_gen.utils import SingletonMeta


logger = logging.getLogger(__name__)


class GIRDocs(metaclass=SingletonMeta):
    """
    Manages the GIR documentation loading and access as a singleton.
    """

    def __init__(self) -> None:
        self._gir_path: Path | None = None
        self._module_gir_docs: ModuleDocs | None = None

    @classmethod
    def reset(cls) -> None:
        if cls in SingletonMeta._instances:
            del SingletonMeta._instances[cls]

    @property
    def loaded_docs(self) -> ModuleDocs | None:
        """Get the currently loaded module documentation object."""
        return self._module_gir_docs

    def load(self, gir_path: Path) -> bool:
        """
        Parse and load a GIR file.
        Overwrites any previously loaded documentation.
        """
        if not gir_path.exists():
            logger.warning(f"GIR file not found at path: {gir_path}")
            return False

        logger.info(f"Loading GIR docs from: {gir_path}")
        docs = parse_gir_docs(gir_path)

        if not docs:
            logger.warning(f"Failed to parse GIR docs from: {gir_path}")
            return False

        self._gir_path = gir_path
        self._module_gir_docs = docs
        return True

    def get_constant_docs(self, constant_name: str) -> str | None:
        """
        Get the parsed documentation for a constant.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        return self._module_gir_docs.constants.get(constant_name, None)

    def get_function_docstring(self, function_name: str) -> str | None:
        """
        Get the parsed documentation for a function.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        if function_name not in self._module_gir_docs.functions:
            return None

        return self._module_gir_docs.functions[function_name].docstring

    def get_function_param_docstring(
        self,
        function_name: str,
        param_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific function parameter.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        func_docs = self._module_gir_docs.functions.get(function_name)
        if func_docs and param_name in func_docs.params:
            return func_docs.params[param_name]

        return None

    def get_function_return_docstring(
        self,
        function_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific function return value.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        func_docs = self._module_gir_docs.functions.get(function_name)
        if func_docs:
            return func_docs.return_doc

        return None

    def get_class_docstring(self, class_name: str) -> str | None:
        """
        Get the parsed documentation for a class.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        class_docs = self._module_gir_docs.classes.get(class_name)
        if class_docs:
            return class_docs.class_docstring

        return None

    def get_class_field_docstring(
        self,
        class_name: str,
        field_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific class field.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        class_docs = self._module_gir_docs.classes.get(class_name)
        if class_docs and field_name in class_docs.fields:
            return class_docs.fields[field_name]
        return None

    def get_class_method_docstring(
        self,
        class_name: str,
        method_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific class method.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        class_docs = self._module_gir_docs.classes.get(class_name)
        if class_docs and method_name in class_docs.methods:
            return class_docs.methods[method_name].docstring
        return None

    def get_class_signal_docstring(
        self,
        class_name: str,
        signal_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific class signal.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        class_docs = self._module_gir_docs.classes.get(class_name)
        if class_docs and signal_name in class_docs.signals:
            return class_docs.signals[signal_name].docstring
        return None

    def get_class_property_docstring(
        self,
        class_name: str,
        property_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific class property.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        class_docs = self._module_gir_docs.classes.get(class_name)
        if class_docs and property_name in class_docs.properties:
            return class_docs.properties[property_name]
        return None

    def get_enum_docstring(
        self,
        enum_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific enum/flag.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        enum_docs = self._module_gir_docs.enums.get(enum_name)
        if enum_docs:
            return enum_docs.class_docstring
        return None

    def get_enum_field_docstring(
        self,
        enum_name: str,
        field_name: str,
    ) -> str | None:
        """
        Get the parsed documentation for a specific enum/flag field.
        """
        if not self._module_gir_docs:
            # logger.warning("GIR docs not loaded, please load a GIR file first using GIRDocs.load()")
            return None

        enum_docs = self._module_gir_docs.enums.get(enum_name)
        if enum_docs and field_name in enum_docs.fields:
            return enum_docs.fields[field_name]
        return None
