from __future__ import annotations

import keyword
from typing import Literal
from pydantic import Field, PrivateAttr
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.schema import BaseSchema


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

    type_imports: set[str] = Field(default_factory=set)
    """Namespaces embedded in a container annotation or callback return annotation."""

    line_comment: str | None
    """line comment for the argument."""

    default_value: str | None
    """Default value"""

    is_pointer: bool
    """Whether this argument is a pointer type"""

    is_variadic: bool = False
    """Whether this argument is variadic (i.e., part of *args)"""

    type_hint_cb_return_name: str | None = None
    """If is a callback, the callback return name for type hinting"""

    type_hint_cb_return_namespace: str | None = None
    """If is a callback, the callback return namespace for type hinting"""

    type_var_name: str | None = None
    """TypeVar name to render instead of the GI argument type, if any."""

    is_marshaled_gvalue_payload: bool = False
    """Whether PyGObject marshals a GValue as its Python payload."""

    # @property
    # def default_value(self) -> str | None:
    #     """Get the default value representation for optional arguments."""
    #     if self.is_optional or self.may_be_null:
    #         return "None"
    #     return None

    @property
    def name_is_keyword(self):
        """
        Check if the function argument name is a python keyword
        This is possible since the name is originally from the GI and not python
        """
        return keyword.iskeyword(self.name)

    def render_type_annotation(self, namespace: str) -> str:
        """
        type representation in template.
        computed with respect to the given namespace.

        if is in the same we avoid adding the namespace prefix.
        """

        base_type = self.type_var_name or self.py_type_name

        if self.direction == "INOUT":
            # INOUT in Python non è tipato diversamente in ingresso,
            # ma semanticamente è importante sapere che può essere modificato?
            # Solitamente nei type hint si usa solo il tipo base.
            pass

        full_type = base_type

        if self.type_var_name is None and self.py_type_namespace and self.py_type_namespace != namespace:
            full_type = f"{self.py_type_namespace}.{base_type}"

        if full_type != "typing.Any" and (self.may_be_null or (self.is_optional and self.direction in ("IN", "INOUT"))):
            full_type = f"{full_type} | None"

        if (
            self.is_callback
            and self.type_hint_cb_return_name is not None
            and self.type_hint_cb_return_namespace is not None
        ):
            cb_return_type = self.type_hint_cb_return_name
            if self.type_hint_cb_return_namespace != namespace:
                cb_return_type = f"{self.type_hint_cb_return_namespace}.{cb_return_type}"
            # add generic Callable type other than the Protocol
            # to be more flexible
            full_type = f"{full_type} | typing.Callable[..., {cb_return_type}]"

        return full_type

    def render_parameter(self, namespace: str, force_no_default: bool = False) -> str:
        """Return one Python parameter as a string, without a trailing comment."""
        annotation = self.render_type_annotation(namespace)
        if self.is_variadic:
            return f"*{self.name}: {annotation}"
        parameter = f"{self.name}: {annotation}"
        if not force_no_default and (self.may_be_null or self.is_optional or self.default_value is not None):
            default = self.default_value if self.default_value is not None else "None"
            parameter += f" = {default}"
        return parameter


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
    """namespace of the return hint, e.g. gi.repository.<NAME> import for the property type, if any"""

    return_type_imports: set[str] = Field(default_factory=set)
    """Namespaces embedded in the return annotation."""

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

    is_overridden: bool = False
    """Whether this function was overridden by a python override. This info will be added
    when parsing the overrides not at parsing time."""

    is_class_member: bool = False
    """Whether this function belongs to a class (as opposed to being a module-level function).
    Used to determine if @staticmethod decorator should be added."""

    is_property: bool = False
    """Whether this function should be rendered as a @property.
    This is used for explicit property overrides (e.g., GEnum.value_name).
    Note: is_getter flag from GI does NOT mean it's a Python property - it just means
    it's a C getter function, which is still a regular method in Python."""

    def render_decorators(self) -> list[str]:
        """
        Return a list of decorator strings based on the function properties.
        """
        decs = []
        if self.is_deprecated:
            deprecation_msg = self.deprecation_warnings or "deprecated"
            decs.append(f'@deprecated("{deprecation_msg}")')

        if self.is_constructor:
            decs.append("@classmethod")

        if self.is_class_member and not self.is_constructor and not self.is_method:
            decs.append("@staticmethod")

        if self.is_property:
            decs.append("@builtins.property")

        if self.is_overload:
            decs.append("@typing.overload")

        return decs

    def render_receiver(self) -> str | None:
        """Return stub text, or None when absent."""
        if self.is_method:
            return "self"
        elif self.is_constructor:
            return "cls"
        elif self.is_callback:
            if len(self.input_args) > 0 and self.args[0].name != "self":
                return "self"
            elif len(self.input_args) == 0:
                return "self"
        return None

    @property
    def input_args(self):
        return [arg for arg in self.args if arg.direction in ("IN", "INOUT")]

    @property
    def output(self):
        return [arg for arg in self.args if arg.direction in ("OUT", "INOUT")]

    @property
    def required_imports(self) -> set[str]:
        gi_imports = set(self.return_type_imports)
        # check return type
        if self.return_hint_namespace:
            gi_imports.add(self.return_hint_namespace)
        if self.return_hint and "typing." in self.return_hint:
            gi_imports.add("typing")
        # check arguments
        for arg in self.args:
            if arg.type_var_name is None:
                gi_imports.update(arg.type_imports)
            if arg.py_type_namespace and arg.type_var_name is None:
                gi_imports.add(arg.py_type_namespace)
            if "typing." in arg.py_type_name:
                gi_imports.add("typing")
        # check decorators
        if self.is_overload:  # we add typing.overload
            gi_imports.add("typing")
        if self.is_property:  # we add builtins.property
            gi_imports.add("builtins")
        return gi_imports

    def render_return_annotation(self, namespace: str) -> str:
        """
        Compute the real Python return hint combining C return and OUT arguments.

        is computed with respect to the given namespace.
        if is in the same we avoid adding the namespace prefix.
        """

        return_parts = []
        # add c return type if not skipped
        if not self.skip_return and self.return_hint is not None:
            return_value = self.return_hint

            if self.return_hint_namespace and self.return_hint_namespace != namespace:
                return_value = f"{self.return_hint_namespace}.{return_value}"

            if self.may_return_null and return_value != "typing.Any":
                return_value = f"{return_value} | None"

            return_parts.append(return_value)

        # if direction is out or inout, add to return type
        for i, arg in enumerate(self.args):
            if arg.direction in ("OUT", "INOUT"):
                return_parts.append(arg.render_type_annotation(namespace=namespace))

        if not return_parts:
            return "None"

        if len(return_parts) == 1:
            return return_parts[0]

        return f"tuple[{', '.join(return_parts)}]"

    def render_stub(self) -> str:
        """Return stub text as a string."""
        return TemplateManager.render_master("function.jinja", fun=self)

    def render_stub_compact(self) -> str:
        """Return stub text as a string."""
        return TemplateManager.render_master("function_compact.jinja", fun=self)

    def render_parameter_list(self, namespace: str, one_line: bool = True) -> str:
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

        for arg in reversed(self.args):
            if arg.direction == "OUT":
                continue

            arg_repr = arg.render_parameter(namespace, force_no_default=not allow_default)
            if not arg.is_variadic and not (arg.may_be_null or arg.is_optional or arg.default_value is not None):
                # Once we find a required parameter, preceding parameters cannot have defaults.
                allow_default = False

            # add line comment if any
            if not one_line and arg.line_comment:
                arg_comment = arg.line_comment
            else:
                arg_comment = None
            argument_list.append((arg_repr, arg_comment))

        # add self or cls if method
        receiver = self.render_receiver()
        if receiver is not None:
            argument_list.append((receiver, None))

        # restore the order
        argument_list.reverse()
        return TemplateManager.render_master(
            "function_args.jinja",
            argument_list=argument_list,
            one_line=one_line,
        )


class CallbackSchema(BaseSchema):
    name: str
    """Callback name"""

    # docstring: str | None = None
    function: FunctionSchema

    originated_from: set[str] | None = None
    """Module or class where the callback was found, if any"""

    @property
    def required_imports(self) -> set[str]:
        gi_imports: set[str] = set()
        # check return type
        gi_imports.add("typing")
        # check arguments
        gi_imports.update(self.function.required_imports)
        return gi_imports

    @property
    def docstring(self) -> str | None:
        docstring: str | None = None

        if self.originated_from is not None:
            docstring = f"This callback was used in: \n\t{', '.join(sorted(self.originated_from))}"

        # func_docstring = self.function.docstring
        # if func_docstring is None:
        #     return None

        return docstring

    def render_stub(self) -> str:
        """Return stub text as a string."""
        return TemplateManager.render_master("callback.jinja", cb=self)
