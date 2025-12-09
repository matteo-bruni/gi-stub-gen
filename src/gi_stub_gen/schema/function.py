from __future__ import annotations

from enum import StrEnum
import inspect
import keyword
import logging
from gi_stub_gen.gi_utils import get_gi_type_info, get_safe_gi_array_length
from gi_stub_gen.manager import TemplateManager
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.utils import (
    catch_gi_deprecation_warnings,
    get_py_type_name_repr,
    get_py_type_namespace_repr,
)
from gi_stub_gen.utils import (
    gi_type_is_callback,
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


class BuiltinFunctionSchema(BaseSchema):
    name: str
    namespace: str
    is_async: bool = False
    docstring: str
    return_hint: str
    params: list[BuiltinFunctionArgumentSchema]

    def render(self) -> str:
        return TemplateManager.render_master("builtin_function.jinja", fun=self)

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

    line_comment: str | None
    """line comment for the argument."""

    @classmethod
    def from_gi_object(
        cls,
        obj: Any,
        direction: Literal["IN", "OUT", "INOUT"],
        parent_namespace: str,  # namespace of the function parent
    ) -> tuple[Self, CallbackSchema | None]:
        found_callback: CallbackSchema | None = None

        gi_type = get_gi_type_info(obj)
        py_type = gi_type_to_py_type(gi_type)

        py_type_name_repr = "Any"  # default

        is_callback = gi_type_is_callback(gi_type)
        argument_namespace = obj.get_namespace()
        line_comment = None
        # Check if it is a Callback
        if is_callback:
            # Get the interface (The actual CallbackInfo)
            cb_info = gi_type.get_interface()
            cb_name = f"{cb_info.get_name()}"
            cb_namespace = cb_info.get_namespace()
            # cb_name = f"{cb_info.get_name()}CB"
            # if parent_namespace == "":
            # if cb_name == "Gio.DestroyNotify":
            #     breakpoint()
            py_type_namespace = cb_namespace
            if cb_namespace != parent_namespace:
                # The callback is defined in another namespace
                # use the fully qualified name
                # since we don't know it is defined there we just add a line comment
                line_comment = "type: ignore"
            else:
                # if cb_name == "DestroyNotify":
                #     breakpoint()
                # the callback is defined in the same namespace
                # create the CallbackSchema

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
            py_type_namespace = get_py_type_namespace_repr(py_type)
            py_type_name_repr = get_py_type_name_repr(py_type)

        array_length: int = get_safe_gi_array_length(gi_type)

        return cls(
            namespace=argument_namespace,
            name=obj.get_name(),
            is_callback=is_callback,
            is_optional=obj.is_optional(),
            may_be_null=obj.may_be_null(),
            direction=direction,
            py_type_namespace=py_type_namespace,
            py_type_name=py_type_name_repr,
            is_deprecated=gi_type.is_deprecated(),
            tag_as_string=gi_type.get_tag_as_string(),
            get_array_length=array_length,
            line_comment=line_comment,
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

        if self.may_be_null:
            full_type = f"{full_type} | None"

        return full_type

    # def __str__(self):
    #     deprecated = "[DEPRECATED]" if self.is_deprecated else ""
    #     return (
    #         f"name={self.name} [keyword={self.name_is_keyword}] {deprecated}"
    #         f"is_optional={self.is_optional} "
    #         f"may_be_null={self.may_be_null} "
    #         # f"_gi_type={self._gi_type} "
    #         f"direction={self.direction} "
    #         # f"py_type={self.py_type} "
    #         f"is_callback={self.is_callback} "
    #         f"tag_as_string={self.tag_as_string} "
    #         f"get_array_length={self.get_array_length} "
    #         f"repr={self.type_hint} "
    #     )


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
    can_throw_gerror: bool
    """Whether this function can throw a GError"""
    may_return_null: bool

    return_hint: str
    """Just the return type hint from GI. Does not include OUT arguments."""

    deprecation_warnings: str | None
    """Deprecation warning message, if any captured """

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
        # add c return type if not skipped
        if not self.skip_return:
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

    @classmethod
    def from_gi_object(
        cls,
        obj: Any,
        docstring: str | None = None,
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
                parent_namespace=obj.get_namespace(),
            )
            function_args.append(function_arg)
            if found_callback:
                # Found a callback argument
                # append to its originated_from info
                found_callback.originated_from = {
                    f"{obj.get_namespace()}.{obj.get_name()}"
                }
                args_as_callbacks_found.append(found_callback)

        # TODO: what happen if return type is another gi type?
        # i.e can a function return a Gst.Caps() object?
        py_return_type = gi_type_to_py_type(obj.get_return_type())
        # get the repr of the return type
        py_return_type_namespace = get_py_type_namespace_repr(py_return_type)
        py_return_type_name = get_py_type_name_repr(py_return_type)

        namespace = obj.get_namespace()
        may_return_null = obj.may_return_null()
        is_callback = isinstance(obj, GI.CallbackInfo)

        # get the return hint for the template
        return_hint = py_return_type_name
        # if may_return_null:
        #     return_hint = f"{return_hint} | None"

        # if obj.get_name() == "get_redirect_target":
        #     breakpoint()

        # add namespace if it is different from the current namespace
        # (e.g., returning 'Gdk.Event' inside 'Gtk' module)
        # if py_return_type_namespace and py_return_type_namespace != namespace:
        #     return_hint = f"{py_return_type_namespace}.{return_hint}"

        if not is_callback:
            flags = obj.get_flags()
            is_constructor = bool(flags & GIRepository.FunctionInfoFlags.IS_CONSTRUCTOR)
            is_getter = bool(flags & GIRepository.FunctionInfoFlags.IS_GETTER)
            is_setter = bool(flags & GIRepository.FunctionInfoFlags.IS_SETTER)
            is_async = bool(flags & GIRepository.FunctionInfoFlags.IS_ASYNC)
            wrap_vfunc = bool(flags & GIRepository.FunctionInfoFlags.WRAPS_VFUNC)
            is_method = obj.is_method()
        else:
            # Callbacks do not have these flags
            is_constructor = False
            is_getter = False
            is_setter = False
            is_async = False
            wrap_vfunc = False
            is_method = False

        to_return = cls(
            namespace=namespace,
            name=obj.get_name(),
            args=function_args,
            is_callback=is_callback,
            docstring=docstring,
            may_return_null=may_return_null,
            can_throw_gerror=obj.can_throw_gerror(),
            is_deprecated=obj.is_deprecated(),
            skip_return=obj.skip_return(),
            return_hint=return_hint,
            deprecation_warnings=catch_gi_deprecation_warnings(
                namespace, obj.get_name()
            ),
            is_method=is_method,
            return_hint_namespace=py_return_type_namespace,
            is_async=is_async,
            is_getter=is_getter,
            is_setter=is_setter,
            is_constructor=is_constructor,
            wrap_vfunc=wrap_vfunc,
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
            docstring = (
                f"This callback was used in: \n\t\t\t{', '.join(self.originated_from)}"
            )

        # func_docstring = self.function.docstring
        # if func_docstring is None:
        #     return None

        return docstring

    def render(self) -> str:
        return TemplateManager.render_master("callback.jinja", cb=self)
