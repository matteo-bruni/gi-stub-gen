from __future__ import annotations

from enum import StrEnum
import inspect
import keyword
import logging
from gi_stub_generator.gi_utils import get_gi_type_info, get_safe_gi_array_length
from gi_stub_generator.parser.gir import ClassDocs, FunctionDocs
from gi_stub_generator.schema import BaseSchema
from gi_stub_generator.utils import (
    catch_gi_deprecation_warnings,
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    get_super_class_name,
    get_type_hint,
    infer_type_str,
    get_redacted_stub_value,
    sanitize_module_name,
)
from gi_stub_generator.utils import (
    gi_type_is_callback,
    gi_type_to_py_type,
    is_py_builtin_type,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    computed_field,
    SerializerFunctionWrapHandler,
    model_validator,
)
import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject
from typing import Literal, Any, Self


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class ArgKind(StrEnum):
    POSITIONAL_OR_KEYWORD = "POS_OR_KW"  # Standard (a)
    POSITIONAL_ONLY = "POS_ONLY"  # Python 3.8+ (a, /)
    KEYWORD_ONLY = "KW_ONLY"  # (*, a)
    VAR_POSITIONAL = "VAR_POS"  # *args
    VAR_KEYWORD = "VAR_KW"  # **kwargs

    @classmethod
    def from_inspect(cls, kind: inspect._ParameterKind) -> "ArgKind":
        """
        Factory method to convert inspect.Parameter.kind to ArgKind.
        """
        # Mapping definition (optimized via dict lookup)
        mapping = {
            inspect.Parameter.POSITIONAL_ONLY: cls.POSITIONAL_ONLY,
            inspect.Parameter.KEYWORD_ONLY: cls.KEYWORD_ONLY,
            inspect.Parameter.VAR_POSITIONAL: cls.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD: cls.VAR_KEYWORD,
            # POSITIONAL_OR_KEYWORD is the default fallback
        }
        return mapping.get(kind, cls.POSITIONAL_OR_KEYWORD)


class BuiltinFunctionArgumentSchema(BaseModel):
    name: str
    type_hint: str = Field(
        description="String representation of the type",
    )
    kind: ArgKind
    default_value: str | None = Field(
        None,
        description="Reprr string of default value. None if required.",
    )

    @property
    def is_required(self) -> bool:
        return self.default_value is None and self.kind not in (
            ArgKind.VAR_POSITIONAL,
            ArgKind.VAR_KEYWORD,
        )

    @property
    def as_str(self) -> str:
        """Returns the formatted argument string: 'name: type = default'"""
        prefix = {ArgKind.VAR_POSITIONAL: "*", ArgKind.VAR_KEYWORD: "**"}.get(
            self.kind, ""
        )

        # Only add default if it exists and is not *args/**kwargs
        default = ""
        if self.default_value is not None and self.kind not in (
            ArgKind.VAR_POSITIONAL,
            ArgKind.VAR_KEYWORD,
        ):
            default = f" = {self.default_value}"

        return f"{prefix}{self.name}: {self.type_hint}{default}"


class BuiltinFunctionSchema(BaseModel):
    name: str
    namespace: str
    is_async: bool = False
    docstring: str
    return_hint: str
    params: list[BuiltinFunctionArgumentSchema]

    @property
    def debug(self):
        """
        Debug docstring
        """
        return f"{self.docstring}\n[DEBUG]\n{self.model_dump_json(indent=2)}"

    @property
    def param_signature(self) -> list[str]:
        """Generates the full parameter string with '/' and '*' separators."""
        # 1. Group params by kind efficiently
        groups = {k: [] for k in ArgKind}
        for p in self.params:
            groups[p.kind].append(p.as_str)

        # 2. Build the parts list
        parts = []

        # A. Positional Only (add '/' if present)
        if groups[ArgKind.POSITIONAL_ONLY]:
            parts.extend(groups[ArgKind.POSITIONAL_ONLY])
            parts.append("/")

        # B. Standard Positional/Keyword
        parts.extend(groups[ArgKind.POSITIONAL_OR_KEYWORD])

        # C. Handle *args or bare '*' separator
        if groups[ArgKind.VAR_POSITIONAL]:
            parts.extend(groups[ArgKind.VAR_POSITIONAL])
        elif groups[ArgKind.KEYWORD_ONLY]:
            parts.append("*")  # Bare asterisk for Keyword-Only args without *args

        # D. Keyword Only & **kwargs
        parts.extend(groups[ArgKind.KEYWORD_ONLY])
        parts.extend(groups[ArgKind.VAR_KEYWORD])

        return parts


class FunctionArgumentSchema(BaseSchema):
    """gi.ArgInfo"""

    namespace: str
    name: str
    is_optional: bool
    direction: Literal["IN", "OUT", "INOUT"]
    # _object: Any

    is_callback: bool
    """Whether this function is a callback"""

    may_be_null: bool
    """Whether this function argument may be null"""

    is_deprecated: bool
    """Whether this function argument is deprecated"""

    tag_as_string: str
    """The tag as string, if any"""

    get_array_length: int
    """The array length of the argument, if applicable"""

    py_type_name: str
    """The python type name of the argument to be used in templates"""

    py_type_namespace: str | None
    """The python type namespace of the argument to be used in templates"""

    @classmethod
    def from_gi_object(
        cls,
        obj: Any,
        direction: Literal["IN", "OUT", "INOUT"],
    ) -> tuple[Self, CallbackSchema | None]:
        found_callback: CallbackSchema | None = None

        gi_type = get_gi_type_info(obj)
        py_type = gi_type_to_py_type(gi_type)

        py_type_name_repr = "Any"  # default

        is_callback = gi_type_is_callback(gi_type)
        # Check if it is a Callback
        if is_callback:
            # Get the interface (The actual CallbackInfo)
            cb_info = gi_type.get_interface()
            cb_name = f"{cb_info.get_name()}Callback"

            cb_schema = FunctionSchema.from_gi_object(cb_info)
            found_callback = CallbackSchema(
                name=cb_name,
                function=cb_schema,
            )

            # use the callback name as the type
            py_type_name_repr = cb_name

        else:
            # Standard type logic
            py_type = gi_type_to_py_type(gi_type)
            py_type_name_repr = get_py_type_name_repr(py_type)

        # TODO: create a protocol for callbacks
        # py_type_name_repr = (
        #     f"TODOProtocol({py_type})"
        #     if gi_type_is_callback(gi_type)
        #     else get_py_type_name_repr(py_type)
        # )

        array_length: int = get_safe_gi_array_length(gi_type)
        return cls(
            namespace=obj.get_namespace(),
            name=obj.get_name(),
            is_callback=is_callback,
            is_optional=obj.is_optional(),
            may_be_null=obj.may_be_null(),
            direction=direction,
            py_type_namespace=get_py_type_namespace_repr(py_type),
            py_type_name=py_type_name_repr,
            is_deprecated=gi_type.is_deprecated(),
            tag_as_string=gi_type.get_tag_as_string(),
            get_array_length=array_length,
        ), found_callback

    @property
    def name_is_keyword(self):
        """
        Check if the function argument name is a python keyword
        This is possible since the name is originally from the GI and not python
        """
        return keyword.iskeyword(self.name)

    @property
    def type_hint(self):
        """
        type representation in template
        """
        # is_nullable = " | None" if self.may_be_null else ""
        # if self.py_type_namespace and self.py_type_namespace != self.namespace:
        #     return f"{self.py_type_namespace}.{self.py_type_name}{is_nullable}"
        # return f"{self.py_type_name}{is_nullable}"

        base_type = self.py_type_name

        # Se è un array, la rappresentazione dovrebbe probabilmente essere list[...]
        # Nota: questo richiede che py_type_name sia stato risolto correttamente prima

        if self.direction == "INOUT":
            # INOUT in Python non è tipato diversamente in ingresso,
            # ma semanticamente è importante sapere che può essere modificato?
            # Solitamente nei type hint si usa solo il tipo base.
            pass

        full_type = base_type
        if self.py_type_namespace and self.py_type_namespace != self.namespace:
            full_type = f"{self.py_type_namespace}.{base_type}"

        # Gestione Optional
        # In Python, un argomento opzionale (con valore di default) non è per forza Nullable.
        # Ma may_be_null significa che accetta None.
        if self.may_be_null:
            full_type = f"{full_type} | None"

        return full_type

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        return (
            f"name={self.name} [keyword={self.name_is_keyword}] {deprecated}"
            f"is_optional={self.is_optional} "
            f"may_be_null={self.may_be_null} "
            # f"_gi_type={self._gi_type} "
            f"direction={self.direction} "
            # f"py_type={self.py_type} "
            f"is_callback={self.is_callback} "
            f"tag_as_string={self.tag_as_string} "
            f"get_array_length={self.get_array_length} "
            f"repr={self.type_hint} "
        )


class FunctionSchema(BaseSchema):
    namespace: str
    name: str
    args: list[FunctionArgumentSchema]
    docstring: FunctionDocs | None

    is_callback: bool
    """Whether this function is a callback"""

    # Keep track of callbacks found during function argument parsing
    _gi_callbacks: list[CallbackSchema] = PrivateAttr(default_factory=list)
    """Callbacks found during function argument parsing, if any"""

    skip_return: bool

    is_deprecated: bool
    can_throw_gerror: bool
    """Whether this function can throw a GError"""
    may_return_null: bool
    is_method: bool
    """Whether this function is a method of a class"""
    return_hint: str
    """Just the return type hint from GI. Does not include OUT arguments."""

    @property
    def input_args(self):
        return [arg for arg in self.args if arg.direction in ("IN", "INOUT")]

    @property
    def output(self):
        return [arg for arg in self.args if arg.direction in ("OUT", "INOUT")]

    @property
    def complete_return_hint(self) -> str:
        """
        Compute the real Python return hint combining C return and OUT arguments.
        """

        return_parts = []

        # add c return type if not skipped
        if not self.skip_return:
            return_parts.append(
                self.return_hint
            )  # Già calcolato come nullable se serve

        # if direction is out or inout, add to return type
        for i, arg in enumerate(self.args):
            if arg.direction in ("OUT", "INOUT"):
                # Nota: per gli INOUT, Python accetta il valore in input
                # e lo restituisce (modificato) in output nella tupla di ritorno.
                return_parts.append(arg.type_hint)

        if not return_parts:
            return "None"

        if len(return_parts) == 1:
            return return_parts[0]

        return f"tuple[{', '.join(return_parts)}]"

    @classmethod
    def from_gi_object(
        cls,
        obj: Any,
        docstring: FunctionDocs | None = None,
    ):
        assert isinstance(obj, GI.CallbackInfo) or isinstance(obj, GI.FunctionInfo), (
            "Not a valid GI function or callback object"
        )

        function_args: list[FunctionArgumentSchema] = []

        # --- 1. Identify Arguments to Skip ---
        # In C, arrays often come as pairs: (data_pointer, length).
        # In Python, we only pass the list/array. PyGObject hides the length argument automatically.
        # We must identify which argument indices correspond to these lengths to exclude them from the signature.
        indices_to_skip: set[int] = set()

        # keep track of callbacks found during function argument parsing
        args_as_callbacks_found: list[CallbackSchema] = []
        """callbacks found during function argument parsing"""

        # first loop to identify indices to skip
        obj_arguments = list(obj.get_arguments())
        for i, arg in enumerate(obj_arguments):
            # Use a safe wrapper to get TypeInfo (handles PyGObject version diffs)
            arg_type = get_gi_type_info(arg)
            array_length: int = get_safe_gi_array_length(arg_type)
            if array_length >= 0:
                indices_to_skip.add(array_length)
            # TODO: add logic to skip 'user_data' and 'GDestroyNotify'
            # for callbacks, but that is more complex and depends on specific GI flags (Closure/Destroy).

        for i, arg in enumerate(obj_arguments):
            # Skip this argument if it was identified as an internal C
            # implementation detail (like array length)
            if i in indices_to_skip:
                continue

            direction: Literal["IN", "OUT", "INOUT"]
            if arg.get_direction() == GI.Direction.OUT:
                direction = "OUT"
            elif arg.get_direction() == GI.Direction.IN:
                direction = "IN"
            elif arg.get_direction() == GI.Direction.INOUT:
                direction = "INOUT"
            else:
                raise ValueError(f"Unknown GI.Direction: {arg.get_direction()}")

            # IMPORTANT: For standard Function Stubs, arguments marked as 'OUT'
            # are NOT part of the Python input signature. They are returned in the tuple.
            # However, 'INOUT' arguments ARE passed as input (and returned modified).
            if direction == "OUT":
                continue

            function_arg, found_callback = FunctionArgumentSchema.from_gi_object(
                obj=arg,
                direction=direction,
            )
            function_args.append(function_arg)
            if found_callback:
                # Found a callback argument
                # append to its originated_from info
                found_callback.originated_from = {
                    f"{obj.get_namespace()}.{obj.get_name()}"
                }
                args_as_callbacks_found.append(found_callback)

        py_return_type = gi_type_to_py_type(obj.get_return_type())
        # get the repr of the return type
        py_return_type_namespace = get_py_type_namespace_repr(py_return_type)
        py_return_type_name = get_py_type_name_repr(py_return_type)

        namespace = obj.get_namespace()
        may_return_null = obj.may_return_null()
        is_callback = isinstance(obj, GI.CallbackInfo)

        # get the return hint for the template
        return_hint = py_return_type_name
        if may_return_null:
            return_hint = f"{return_hint} | None"

        # add namespace if it is different from the current namespace
        # (e.g., returning 'Gdk.Event' inside 'Gtk' module)
        if py_return_type_namespace and py_return_type_namespace != namespace:
            return_hint = f"{py_return_type_namespace}.{return_hint}"

        # if len(args_as_callbacks_found) > 0:
        #     print(
        #         f"Function {namespace}.{obj.get_name()} has callbacks as argument: {[cb[0] for cb in args_as_callbacks_found]}"
        #     )
        # if is_callback:
        #     print(f"Function {namespace}.{obj.get_name()} is a callback )")

        to_return = cls(
            namespace=namespace,
            name=obj.get_name(),
            args=function_args,
            is_callback=is_callback,
            docstring=docstring,
            may_return_null=may_return_null,
            is_method=False if is_callback else obj.is_method(),
            can_throw_gerror=obj.can_throw_gerror(),
            is_deprecated=obj.is_deprecated(),
            skip_return=obj.skip_return(),
            return_hint=return_hint,
        )
        to_return._gi_callbacks = args_as_callbacks_found
        return to_return

    @property
    def debug(self):
        """
        Debug docstring
        """

        data = ""
        if self.docstring:
            data = f"{self.docstring}"

        return f"{data}\n[DEBUG]\n{self.model_dump_json(indent=2)}"


class CallbackSchema(BaseSchema):
    name: str
    """Callback name"""

    # docstring: str | None = None
    function: FunctionSchema

    originated_from: set[str] | None = None
    """Module or class where the callback was found, if any"""

    @property
    def docstring(self) -> str | None:
        docstring: str | None = None

        if self.originated_from is not None:
            docstring = (
                f"This callback was used in: \n\t\t\t{', '.join(self.originated_from)}"
            )

        # func_docstring = self.function.docstring
        # if func_docstring is None:
        #     return None

        return docstring

    @property
    def debug(self):
        """
        Debug docstring
        """

        data = ""
        if self.docstring:
            data = f"{self.docstring}"

        return f"{data}\n[DEBUG]\n{self.model_dump_json(indent=2)}"
        # return f"[DEBUG]\n{self.model_dump_json(indent=2)}"


#     def render_protocol(self) -> str:
#         """
#         Renders the Python Protocol definition.
#         """
#         # Filter arguments for the __call__ method (usually only IN and INOUT matter for input)
#         # Note: In Python Protocols for callbacks, you usually define the input signature.
#         input_args_str = ", ".join(
#             f"{arg.name}: {arg.type_hint}" for arg in self.function.args
#         )

#         return f"""
# class {self.name}(typing.Protocol):
#     def __call__(self, {input_args_str}) -> {self.function.return_hint}:
#         ...
# """
