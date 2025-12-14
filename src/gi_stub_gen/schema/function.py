from __future__ import annotations

from enum import StrEnum
import inspect
import keyword
import logging
from gi_stub_gen.gi_utils import (
    catch_gi_deprecation_warnings,
    get_gi_type_info,
    get_safe_gi_array_length,
    gi_type_is_callback,
)
from gi_stub_gen.t_manager import TemplateManager
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.utils import (
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    sanitize_variable_name,
)
from gi_stub_gen.gi_utils import (
    gi_type_to_py_type,
)
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
)
from gi.repository import GIRepository
import gi._gi as GI  # pyright: ignore[reportMissingImports]
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
    type_hint_name: str = Field(
        description="String representation of the type",
    )
    type_hint_namespace: str | None = Field(
        None,
        description="Namespace of the type hint. None if not applicable.",
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

    def type_hint(self, namespace: str) -> str:
        """
        type representation in template.
        computed with respect to the given namespace.

        if is in the same we avoid adding the namespace prefix.
        """

        full_type = self.type_hint_name
        if self.type_hint_namespace and self.type_hint_namespace != namespace:
            full_type = f"{self.type_hint_namespace}.{self.type_hint_name}"

        return full_type

    def as_str(self, namespace: str) -> str:
        """Returns the formatted argument string: 'name: type = default'"""
        prefix = {ArgKind.VAR_POSITIONAL: "*", ArgKind.VAR_KEYWORD: "**"}.get(self.kind, "")

        # Only add default if it exists and is not *args/**kwargs
        default = ""
        if self.default_value is not None and self.kind not in (
            ArgKind.VAR_POSITIONAL,
            ArgKind.VAR_KEYWORD,
        ):
            default = f" = {self.default_value}"

        return f"{prefix}{self.name}: {self.type_hint(namespace)}{default}"


class BuiltinFunctionSchema(BaseSchema):
    name: str
    namespace: str
    is_async: bool
    is_method: bool
    docstring: str | None
    return_hint_name: str
    return_hint_namespace: str | None
    params: list[BuiltinFunctionArgumentSchema]

    def render(self) -> str:
        return TemplateManager.render_master("builtin_function.jinja", fun=self)

    def return_hint(self, namespace: str) -> str:
        """
        type representation in template.
        computed with respect to the given namespace.

        if is in the same we avoid adding the namespace prefix.
        """

        full_type = self.return_hint_name
        if self.return_hint_namespace and self.return_hint_namespace != namespace:
            full_type = f"{self.return_hint_namespace}.{self.return_hint_name}"

        return full_type

    def param_signature(self, namespace: str) -> list[str]:
        """Generates the full parameter string with '/' and '*' separators."""
        # 1. Group params by kind efficiently
        groups = {k: [] for k in ArgKind}
        for p in self.params:
            groups[p.kind].append(p.as_str(namespace))

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
    direction: Literal["IN", "OUT", "INOUT"]

    is_optional: bool
    """Whether this function argument is optional"""

    is_callback: bool
    """Whether this function is a callback"""

    may_be_null: bool
    """Whether this function argument may be null"""

    is_deprecated: bool
    """Whether this function argument is deprecated"""

    is_caller_allocates: bool
    """Whether the caller allocates this argument (for OUT parameters)"""

    tag_as_string: str
    """The tag as string, if any"""

    get_array_length: int
    """The array length of the argument, if applicable"""

    py_type_name: str
    """The python type name of the argument to be used in templates"""

    py_type_namespace: str | None
    """The python type namespace of the argument to be used in templates"""

    line_comment: str | None
    """line comment for the argument."""

    default_value: str | None
    """Default value"""

    # @property
    # def default_value(self) -> str | None:
    #     """Get the default value representation for optional arguments."""
    #     if self.is_optional or self.may_be_null:
    #         return "None"
    #     return None

    @classmethod
    def from_gi_object(
        cls,
        obj: GIRepository.ArgInfo,
        direction: Literal["IN", "OUT", "INOUT"],
    ) -> tuple[Self, CallbackSchema | None]:
        found_callback: CallbackSchema | None = None

        function_namespace: str = obj.get_container().get_namespace()
        argument_namespace: str = obj.get_namespace()
        argument_name = obj.get_name()
        assert argument_name is not None, "Argument name is None"

        gi_type: GIRepository.TypeInfo = get_gi_type_info(obj)

        type_hint_namespace: str | None
        type_hint_name: str
        type_hint_comment: str | None = None

        is_callback = gi_type_is_callback(gi_type)

        # callback cant be instantiated directly to python objects
        # so we need to get the interface and create a CallbackSchema
        if is_callback:
            # Get the interface (The actual CallbackInfo)
            cb_info = gi_type.get_interface()
            assert cb_info is not None, "CallbackInfo is None for Callback type"

            cb_name = cb_info.get_name()
            assert cb_name is not None, "CallbackInfo has no name"

            cb_namespace = cb_info.get_namespace()

            # we found all the info to create the type hint
            type_hint_namespace = cb_namespace
            type_hint_name = cb_name

            if cb_namespace != function_namespace:
                # The callback is defined in another namespace
                # use the fully qualified name
                # since we don't know it is defined in that stub
                # (callback stubs are generated only if found as args during parsing)
                # we just add a line comment to avoid typing errors
                type_hint_comment = "type: ignore"
            else:
                # the callback is defined in the same namespace
                # create the CallbackSchema so we later generate its stub
                cb_schema = FunctionSchema.from_gi_object(cb_info)  # type: ignore
                found_callback = CallbackSchema(
                    name=cb_name,
                    function=cb_schema,
                )

        else:
            # Standard type logic
            # we can get the python type from the gi type
            py_type = gi_type_to_py_type(gi_type)
            type_hint_namespace = get_py_type_namespace_repr(py_type)
            type_hint_name = get_py_type_name_repr(py_type)

        array_length: int = get_safe_gi_array_length(gi_type)
        # breakpoint()
        return cls(
            namespace=argument_namespace,
            name=argument_name,
            is_callback=is_callback,
            is_optional=obj.is_optional(),
            may_be_null=obj.may_be_null(),
            direction=direction,
            py_type_namespace=type_hint_namespace,
            py_type_name=type_hint_name,
            is_deprecated=gi_type.is_deprecated(),
            tag_as_string=gi_type.get_tag_as_string(),
            get_array_length=array_length,
            line_comment=type_hint_comment,
            is_caller_allocates=obj.is_caller_allocates(),
            default_value=None,
        ), found_callback

    @property
    def name_is_keyword(self):
        """
        Check if the function argument name is a python keyword
        This is possible since the name is originally from the GI and not python
        """
        return keyword.iskeyword(self.name)

    def type_hint(self, namespace: str) -> str:
        """
        type representation in template.
        computed with respect to the given namespace.

        if is in the same we avoid adding the namespace prefix.
        """

        base_type = self.py_type_name

        if self.direction == "INOUT":
            # INOUT in Python non è tipato diversamente in ingresso,
            # ma semanticamente è importante sapere che può essere modificato?
            # Solitamente nei type hint si usa solo il tipo base.
            pass

        full_type = base_type
        # if self.py_type_namespace and self.py_type_namespace != self.namespace:
        #     full_type = f"{self.py_type_namespace}.{base_type}"

        if self.py_type_namespace and self.py_type_namespace != namespace:
            full_type = f"{self.py_type_namespace}.{base_type}"

        if self.may_be_null or self.is_optional:
            full_type = f"{full_type} | None"

        return full_type


class FunctionSchema(BaseSchema):
    namespace: str
    name: str
    args: list[FunctionArgumentSchema]
    docstring: str | None

    is_callback: bool
    """Whether this function is a callback"""

    # Keep track of callbacks found during function argument parsing
    _gi_callbacks: list[CallbackSchema] = PrivateAttr(default_factory=list)
    """Callbacks found during function argument parsing, if any"""

    skip_return: bool

    is_deprecated: bool
    """Whether this function is deprecated"""

    can_throw_gerror: bool
    """Whether this function can throw a GError"""

    may_return_null: bool
    """Whether this function may return null"""

    deprecation_warnings: str | None
    """Deprecation warning message, if any captured """

    return_hint: str | None
    """Just the return type hint from GI. Does not include OUT arguments. If None, means return void. Use None if no OUT args, otherwise skip it."""

    return_hint_namespace: str | None
    """namespace of the return hint, e.g. gi.repository<NAME> import for the property type, if any"""

    is_method: bool
    """Whether this function is a method of a class"""

    is_async: bool
    """Whether this function is asynchronous (i.e., has a _async variant)"""

    is_getter: bool
    """Whether this function is a getter method"""

    is_setter: bool
    """Whether this function is a setter method"""

    is_constructor: bool
    """Whether this function is a constructor method"""

    wrap_vfunc: bool
    """Whether this function Represents a virtual function."""

    line_comment: str | None
    """line comment for the function if in compact rendering."""

    function_type: Literal["SignalInfo", "FunctionInfo", "CallbackInfo"]
    """Type of GI function object."""

    is_overload: bool
    """Whether this function is an overload of another function."""

    @property
    def decorators(self) -> list[str]:
        """
        Generate decorators for the function based on its properties.
        """
        decs = []
        if self.is_deprecated:
            deprecation_msg = self.deprecation_warnings or "deprecated"
            decs.append(f'@deprecated("{deprecation_msg}")')

        if self.is_constructor:
            decs.append("@classmethod")

        if not self.is_constructor and not self.is_method:
            decs.append("@staticmethod")

        if self.is_getter:
            decs.append("@property")

        if self.is_overload:
            decs.append("@typing.overload")

        return decs

    @property
    def first_arg(self) -> str | None:
        if self.is_method:
            return "self"
        elif self.is_constructor:
            return "cls"
        return None

    @property
    def input_args(self):
        return [arg for arg in self.args if arg.direction in ("IN", "INOUT")]

    @property
    def output(self):
        return [arg for arg in self.args if arg.direction in ("OUT", "INOUT")]

    @property
    def required_gi_imports(self) -> set[str]:
        gi_imports: set[str] = set()
        # check return type
        if self.return_hint_namespace:
            gi_imports.add(self.return_hint_namespace)
        # check arguments
        for arg in self.args:
            if arg.py_type_namespace:
                gi_imports.add(arg.py_type_namespace)
        return gi_imports

    def complete_return_hint(self, namespace: str) -> str:
        """
        Compute the real Python return hint combining C return and OUT arguments.

        is computed with respect to the given namespace.
        if is in the same we avoid adding the namespace prefix.
        """

        return_parts = []
        # if self.name == "version":
        #     breakpoint()
        # add c return type if not skipped
        if not self.skip_return and self.return_hint is not None:
            return_value = self.return_hint

            if self.return_hint_namespace and self.return_hint_namespace != namespace:
                return_value = f"{self.return_hint_namespace}.{return_value}"

            if self.may_return_null:
                return_value = f"{return_value} | None"

            return_parts.append(return_value)

        # if direction is out or inout, add to return type
        for i, arg in enumerate(self.args):
            if arg.direction in ("OUT", "INOUT"):
                return_parts.append(arg.type_hint(namespace=namespace))

        if not return_parts:
            return "None"

        if len(return_parts) == 1:
            return return_parts[0]

        return f"tuple[{', '.join(return_parts)}]"

    def render(self) -> str:
        return TemplateManager.render_master("function.jinja", fun=self)

    def render_compact(self) -> str:
        return TemplateManager.render_master("function_compact.jinja", fun=self)

    def render_args(self, namespace: str, one_line: bool = True) -> str:
        """
        Render the function arguments for the template.
        We need to reverse the args to add default values correctly.

        Args:
            namespace: the current module namespace for type hint resolution
            one_line: whether to render in one line or multi-line format
        Returns:
            The rendered argument string.
        """
        argument_list: list[tuple[str, str | None]] = []
        allow_default = True
        # if self.name == "__init__":
        #     one_line = False

        for arg in reversed(self.args):
            if arg.direction == "OUT":
                continue

            arg_repr = f"{arg.name}: {arg.type_hint(namespace)}"
            # default_value
            # add default value for optional arguments
            is_nullable = arg.may_be_null or arg.is_optional
            if (is_nullable or arg.default_value is not None) and allow_default:
                if arg.default_value is not None:
                    arg_repr = f"{arg_repr} = {arg.default_value}"
                else:
                    arg_repr = f"{arg_repr} = None"
            else:
                # once we find a non-optional, stop adding defaults
                allow_default = False
            # add line comment if any
            if not one_line and arg.line_comment:
                arg_comment = arg.line_comment
            else:
                arg_comment = None
            argument_list.append((arg_repr, arg_comment))

        # add self or cls if method
        if self.first_arg is not None:
            argument_list.append((self.first_arg, None))

        # restore the order
        argument_list.reverse()
        return TemplateManager.render_master(
            "function_args.jinja",
            argument_list=argument_list,
            one_line=one_line,
        )

    @classmethod
    def from_gi_object(
        cls,
        obj: GIRepository.FunctionInfo | GIRepository.CallbackInfo | GIRepository.SignalInfo,
        docstring: str | None = None,
    ):
        # Note cant do isinstance on GIRepository.FunctionInfo!!
        # they are different object, we use GIRepository.FunctionInfo
        # just for the type hinting

        function_type: str
        if isinstance(obj, GI.SignalInfo):
            function_type = "SignalInfo"
        elif isinstance(obj, GI.CallbackInfo):
            function_type = "CallbackInfo"
        elif isinstance(obj, GI.FunctionInfo):
            function_type = "FunctionInfo"
        else:
            raise ValueError("Not a valid GI function or callback object or signal.")

        # breakpoint()
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

        # out_args = []
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
            # if direction == "OUT":
            #     continue

            function_arg, found_callback = FunctionArgumentSchema.from_gi_object(
                obj=arg,
                direction=direction,
            )
            function_args.append(function_arg)
            if found_callback:
                # Found a callback argument
                # append to its originated_from info
                found_callback.originated_from = {f"{obj.get_namespace()}.{obj.get_name()}"}
                args_as_callbacks_found.append(found_callback)

        # TODO: what happen if return type is another gi type?
        # i.e can a function return a Gst.Caps() object?
        py_return_type = gi_type_to_py_type(obj.get_return_type())

        if py_return_type is None:
            py_return_hint_namespace = None
            py_return_hint_name = None
        else:
            # get the repr of the return type
            py_return_hint_namespace = get_py_type_namespace_repr(py_return_type)
            py_return_hint_name = get_py_type_name_repr(py_return_type)

        function_namespace: str = obj.get_namespace()

        f_name = obj.get_name()
        assert f_name is not None, "Function name is None"
        sane_function_name, name_unsafe_comment = sanitize_variable_name(f_name)
        assert sane_function_name is not None, "Function name is None"

        if name_unsafe_comment and function_type == "FunctionInfo":
            # in callback and signal we dont care about keywords
            logger.warning(
                f"Function name '{f_name}' in namespace '{function_namespace}' "
                f"invalid name: '{name_unsafe_comment} -> {sane_function_name}'."
            )
            # we alert via deprecated warning
            is_deprecated = True
            deprecation_warnings = f"Function name '{f_name}' is a Python keyword. Renamed to '{sane_function_name}' in stub. Please use `{f_name}` in your code and add a # type: ignore."
        else:
            is_deprecated = obj.is_deprecated()
            deprecation_warnings = catch_gi_deprecation_warnings(
                function_namespace,
                sane_function_name,
            )

        may_return_null = obj.may_return_null()
        is_callback = isinstance(obj, GI.CallbackInfo)

        # get the return hint for the template
        return_hint = py_return_hint_name

        # if function_name == "version":
        #     breakpoint()

        if not is_callback:
            flags = obj.get_flags()  # type: ignore
            is_constructor = bool(flags & GIRepository.FunctionInfoFlags.IS_CONSTRUCTOR)
            is_getter = bool(flags & GIRepository.FunctionInfoFlags.IS_GETTER)
            is_setter = bool(flags & GIRepository.FunctionInfoFlags.IS_SETTER)
            is_async = bool(flags & GIRepository.FunctionInfoFlags.IS_ASYNC)
            wrap_vfunc = bool(flags & GIRepository.FunctionInfoFlags.WRAPS_VFUNC)
            is_method = obj.is_method() if hasattr(obj, "is_method") else False  # SignalInfo has no is_method()
        else:
            # Callbacks do not have these flags
            is_constructor = False
            is_getter = False
            is_setter = False
            is_async = False
            wrap_vfunc = False
            is_method = False

        line_comment = None
        if py_return_hint_namespace and py_return_hint_namespace.startswith("gi._"):
            line_comment = "type: ignore"

        to_return = cls(
            namespace=function_namespace,
            name=sane_function_name,
            args=function_args,
            is_callback=is_callback,
            docstring=docstring,
            may_return_null=may_return_null,
            can_throw_gerror=obj.can_throw_gerror(),
            is_deprecated=is_deprecated,
            skip_return=obj.skip_return(),
            deprecation_warnings=deprecation_warnings,
            is_method=is_method,
            return_hint=return_hint,
            return_hint_namespace=py_return_hint_namespace,
            is_async=is_async,
            is_getter=is_getter,
            is_setter=is_setter,
            is_constructor=is_constructor,
            wrap_vfunc=wrap_vfunc,
            line_comment=line_comment,
            function_type=function_type,
            is_overload=True if function_type == "SignalInfo" else False,
        )
        to_return._gi_callbacks = args_as_callbacks_found
        return to_return


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
            docstring = f"This callback was used in: \n\t\t\t{', '.join(self.originated_from)}"

        # func_docstring = self.function.docstring
        # if func_docstring is None:
        #     return None

        return docstring

    def render(self) -> str:
        return TemplateManager.render_master("callback.jinja", cb=self)
