from __future__ import annotations

import keyword
import logging
from gi_stub_generator.parser.gir import ClassDocs, FunctionDocs
from gi_stub_generator.utils import (
    catch_gi_deprecation_warnings,
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    get_super_class_name,
    get_type_hint,
    infer_type_str,
    redact_stub_value,
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
    computed_field,
    SerializerFunctionWrapHandler,
    model_validator,
)
import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject
from pydantic.functional_serializers import WrapSerializer
from typing import Annotated, Literal, Any

logger = logging.getLogger(__name__)


class BaseSchema(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


# Custom Type Value Any for Any or None type
# we add a custom serializer to handle the serialization of Any type
# if it not serializable, it will fallback to str(v)
# used for debugging purposes, i.e a variable = dict(gobject_values)
# this is due to some classes having attributes that are not serializable
def ser_variable_wrap(v: Any, fun: SerializerFunctionWrapHandler):
    # return f'{nxt(v + 1):,}'
    try:
        return fun(v)
    except Exception as e:
        # logger.warning(f"[WARNING] Error serializing variable: {e}: {v}")
        # print("[DEBUG] Variable value:", v)
        return str(v)  # Fallback to string representation
    # return fun(v)


ValueAny = Annotated[Any | None, WrapSerializer(ser_variable_wrap, when_used="json")]


class AliasSchema(BaseSchema):
    """
    Represents an alias in the current gi repository,
    i.e. a class or a function that is an alias for another repository object
    """

    name: str
    target_name: str | None
    target_namespace: str | None
    deprecation_warning: str | None
    line_comment: str | None

    @property
    def target_repr(self):
        """
        Return the target representation in template
        """
        if self.target_namespace and self.target_name:
            return f"{self.target_namespace}.{self.target_name}"
        elif self.target_name:
            return self.target_name

        return "..."

    @property
    def docstring(self):
        if self.deprecation_warning:
            return f"[DEPRECATED] {self.deprecation_warning}"

        return None


class VariableSchema(BaseSchema):
    """
    Represents a variable in the gi repository, can be a constant or a variable
    """

    namespace: (
        str  # need to be passed since it is not available in the python std types
    )
    name: str
    value: ValueAny
    # value: Any | None

    is_deprecated: bool
    """Whether this variable is deprecated (from info)"""

    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    type_repr: str
    """type representation in template"""

    value_repr: str
    """value representation in template"""

    gir_docstring: str | None

    is_enum_or_flags: bool
    """Whether this variable is an enum or flags (we avoid writing the type in the template)"""

    @property
    def docstring(self):
        docstring_str: list[str] = []
        if self.deprecation_warnings:
            docstring_str.append(f"[DEPRECATED] {self.deprecation_warnings}")

        if self.gir_docstring:
            docstring_str.append(f"{self.gir_docstring}")

        return "\n".join(docstring_str) or None

    @property
    def debug(self):
        """
        Debug docstring
        """
        if self.docstring:
            return f"{self.docstring}\n[DEBUG]\n{self.model_dump_json(indent=2)}"

        return f"[DEBUG]\n{self.model_dump_json(indent=2)}"

    @classmethod
    def from_gi_object(
        cls,
        obj,
        namespace: str,  # need to be passed since it is not available for python std types
        name: str,
        docstring: str | None,
        deprecation_warnings: str | None = None,
        keep_builtin_value: bool = False,
    ):
        # breakpoint()
        sanitized_namespace = sanitize_module_name(namespace)
        object_type = type(obj)
        object_type_namespace: str | None = None
        if hasattr(obj, "__info__"):
            if obj.__info__.get_namespace() != sanitized_namespace:
                object_type_namespace = str(obj.__info__.get_namespace())

        # type representation in template should include namespace only if
        # it is different from the current namespace
        object_type_repr = object_type.__name__
        if object_type_namespace and object_type_namespace != sanitized_namespace:
            object_type_repr = f"{object_type_namespace}.{object_type_repr}"

        # get value representation in template
        value_repr: str = ""
        is_deprecated = False
        is_enum_or_flags = False

        if is_py_builtin_type(object_type):
            # remove sensitive information from value representation
            # i.e paths from string or
            if keep_builtin_value:
                value_repr = redact_stub_value(obj)
            else:
                value_repr = "..."
            # or remove directly the value from builtin types
            # value_repr = "..."
            # value_repr = repr(obj)
            if isinstance(obj, (dict, list, tuple)):
                # for dicts we also include the type representation
                # value_repr = "..."
                object_type_repr = get_type_hint(obj)

        elif hasattr(obj, "__info__"):
            if hasattr(obj.__info__, "is_deprecated"):
                is_deprecated = obj.__info__.is_deprecated()

            # value is from gi: can be an enum or flags
            # both are GI.EnumInfo
            if type(obj.__info__) is GI.EnumInfo:
                is_flags = obj.__info__.is_flags()
                is_enum_or_flags = True

                if is_flags:
                    if obj.first_value_nick is not None:
                        value_repr = (
                            f"{object_type_repr}.{obj.first_value_nick.upper()}"
                        )
                    else:
                        # Fallback to using the real value
                        value_repr = f"{object_type_repr}({obj.real})"

                if not is_flags:
                    # it is an enum
                    value_repr = f"{object_type_repr}.{obj.value_nick.upper()}"
        elif isinstance(obj, GObject.GType):
            value_repr = "..."
        else:
            # Fallback to using the real value
            print("[WARNING] Object representation not found, using real value")
            value_repr = f"{object_type_repr}({obj}) # TODO: not found ??"

        # if name == "SIGNAL_ACTION":
        #     breakpoint()
        # deprecation_warnings = catch_gi_deprecation_warnings(obj, name)
        return cls(
            namespace=sanitized_namespace,
            name=name,
            type_repr=object_type_repr,
            value=obj,
            value_repr=value_repr,
            is_deprecated=is_deprecated,
            gir_docstring=docstring,
            deprecation_warnings=deprecation_warnings,
            is_enum_or_flags=is_enum_or_flags,
        )

    # model_config = ConfigDict(use_attribute_docstrings=True)

    # def __str__(self):
    #     # print(self.value_repr, self.type)
    #     deprecated = "[DEPRECATED]" if self.is_deprecated else ""
    #     return (
    #         f"namespace={self.namespace} "
    #         f"name={self.name} "
    #         f"type={type(self.value)} "
    #         f"value={self.value} "
    #         f"value_repr={self.value_repr} {deprecated} "
    #         f"is_deprecated={self.is_deprecated} "
    #         f"deprecation_warnings={self.deprecation_warnings} "
    #     )


class EnumFieldSchema(BaseSchema):
    name: str
    value: int
    value_repr: str
    """value representation in template"""

    is_deprecated: bool

    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    docstring: str | None = None

    @classmethod
    def from_gi_value_info(
        cls,
        value_info: GI.ValueInfo,
        docstring: str | None,
        deprecation_warnings: str | None,
    ):
        # TODO:
        # value_info.get_name() != value_info.get_name_unescaped()
        # example: GLib.IOCondition.IN_ vs GLib.IOCondition.IN
        # gobject escape the name in get_name because "in" is a keyword in python
        # for now we just use the unescaped name
        # field_name = value_info.get_name()
        field_name = value_info.get_name_unescaped()
        return cls(
            name=field_name.upper(),
            value=value_info.get_value(),
            value_repr=repr(value_info.get_value()),
            is_deprecated=value_info.is_deprecated(),
            docstring=docstring,
            deprecation_warnings=deprecation_warnings,
        )

    def __str__(self):
        deprecated = "[DEPRECATED] " if self.is_deprecated else ""
        return f"name={self.name} value={self.value} {deprecated}"


class EnumSchema(BaseSchema):
    enum_type: Literal["enum", "flags"]

    name: str
    namespace: str
    is_deprecated: bool
    fields: list[EnumFieldSchema]
    docstring: str | None = None

    py_mro: list[str]
    """Used for debugging purposes"""

    @classmethod
    def from_gi_object(
        cls,
        obj: Any,
        enum_type: Literal["enum", "flags"],
        fields: list[EnumFieldSchema],
        docstring: str | None,
    ):
        assert hasattr(obj, "__info__"), (
            "An Enum/Flags Object must have __info__ attribute"
        )

        gi_info = obj.__info__

        return cls(
            namespace=gi_info.get_namespace(),
            name=gi_info.get_name(),
            enum_type=enum_type,
            docstring=docstring,
            fields=fields,
            is_deprecated=gi_info.is_deprecated(),
            py_mro=[f"{o.__module__}.{o.__name__}" for o in obj.mro()],
        )

    @computed_field
    @property
    def py_super_type_str(self) -> str:
        """Return the python type as a string (otherwise capitalization is wrong)"""

        # in pygobject 3.50.0 GFlags and GEnum are in GObject namespace
        if self.namespace == "GObject":
            return "GFlags" if self.enum_type == "flags" else "GEnum"

        return "GObject.GFlags" if self.enum_type == "flags" else "GObject.GEnum"

        # after pygobject 3.54.0 GFlags and GEnum are normal classes so we can

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        args_str = "\n".join([f"   - {arg}" for arg in self.fields])
        mro = f"mro={self.py_mro}"
        return (
            f"{deprecated}namespace={self.namespace} name={self.name} {mro}\n{args_str}"
        )

    @property
    def debug(self):
        """
        Debug docstring
        """
        return f"{self.docstring}\n[DEBUG]\n{self.model_dump_json(indent=2)}"


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
    ):
        try:
            gi_type = obj.get_type()
        except AttributeError as e:
            # removed in pygobject 3.54.0?? was present in 3.50.0
            # logger.warning(f"Could not get gi type for argument {obj.get_name()}: {e}")
            gi_type = obj.get_type_info()

        py_type = gi_type_to_py_type(gi_type)

        # TODO: create a protocol for callbacks
        py_type_name_repr = (
            f"TODOProtocol({py_type})"
            if gi_type_is_callback(gi_type)
            else get_py_type_name_repr(py_type)
        )

        try:
            array_length: int = gi_type.get_array_length()
        except AttributeError as e:
            # removed in pygobject 3.54.0?? was present in 3.50.0
            # logger.warning(
            #     f"Could not get array length for argument {obj.get_name()}: {e}"
            # )
            # https://valadoc.org/gobject-introspection-1.0/GI.TypeInfo.get_array_length.html
            # the array length, or -1 if the type is not an array
            # somehow in the newer pygobject this method is missing if not an array
            array_length = -1
            # breakpoint()

        return cls(
            namespace=obj.get_namespace(),
            name=obj.get_name(),
            is_callback=gi_type_is_callback(gi_type),
            is_optional=obj.is_optional(),
            may_be_null=obj.may_be_null(),
            direction=direction,
            py_type_namespace=get_py_type_namespace_repr(py_type),
            py_type_name=py_type_name_repr,
            is_deprecated=gi_type.is_deprecated(),
            tag_as_string=gi_type.get_tag_as_string(),
            get_array_length=array_length,
        )

    # def __init__(self, _object, **data):
    #     super().__init__(**data)
    #     self._object = _object

    # @property
    # def _gi_type(self):
    #     return self._object.get_type()

    @property
    def name_is_keyword(self):
        """
        Check if the function argument name is a python keyword
        This is possible since the name is originally from the GI and not python
        """
        return keyword.iskeyword(self.name)

    # @computed_field
    # @property
    # def is_callback(self) -> bool:
    #     return gi_type_is_callback(self._gi_type)

    # @computed_field
    # @property
    # def py_type_namespace(self) -> str | None:
    #     return get_py_type_namespace(self.py_type)

    @property
    def type_repr(self):
        """
        type representation in template
        """
        is_nullable = " | None" if self.may_be_null else ""
        if self.py_type_namespace and self.py_type_namespace != self.namespace:
            return f"{self.py_type_namespace}.{self.py_type_name}{is_nullable}"
        return f"{self.py_type_name}{is_nullable}"

    # @property
    # def py_type_name(self):
    #     if gi_type_is_callback(self._gi_type):
    #         # TODO: registrare protocollo
    #         return f"TODOProtocol({self.py_type})"

    #     if hasattr(self.py_type, "__info__"):
    #         return f"{self.py_type.__info__.get_name()}"  # type: ignore

    #     if hasattr(self.py_type, "__name__"):
    #         return self.py_type.__name__  # type: ignore

    #     return self.py_type

    # @property
    # def py_type(self):
    #     py_type = gi_type_to_py_type(self._gi_type)

    #     # if gi_type_is_callback(self._gi_type):
    #     #     # TODO: registrare protocollo
    #     #     return f"Protocol({py_type})"

    #     return py_type
    #     if hasattr(py_type, "__info__"):
    #         return f"{py_type.__info__.get_namespace()}.{py_type.__info__.get_name()}"

    #     if hasattr(py_type, "__name__"):
    #         return py_type.__name__

    #     return py_type

    # @computed_field
    # @property
    # def is_deprecated(self) -> bool:
    #     return self._gi_type.is_deprecated()

    # @computed_field
    # @property
    # def may_be_null(self) -> bool:
    #     return self._object.may_be_null()

    # @computed_field
    # @property
    # def tag_as_string(self) -> str:
    #     return self._gi_type.get_tag_as_string()

    # @computed_field
    # @property
    # def get_array_length(self) -> int:
    #     return self._gi_type.get_array_length()

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
            f"repr={self.type_repr} "
        )


class BuiltinFunctionSchema(BaseSchema):
    name: str
    namespace: str
    signature: str
    docstring: str
    return_repr: str
    params: list[str]

    # @property
    # def return_repr(self):
    #     """
    #     Return the return type representation in template
    #     """
    #     return self.signature

    @property
    def debug(self):
        """
        Debug docstring
        """
        return f"{self.docstring}\n[DEBUG]\n{self.model_dump_json(indent=2)}"


class FunctionSchema(BaseSchema):
    namespace: str
    name: str
    args: list[FunctionArgumentSchema]
    docstring: FunctionDocs | None

    is_callback: bool
    """Whether this function is a callback"""

    _gi_callbacks: list[Any] = []
    """Callbacks found during function argument parsing, if any"""

    skip_return: bool

    is_deprecated: bool
    can_throw_gerror: bool
    """Whether this function can throw a GError"""
    may_return_null: bool
    is_method: bool
    """Whether this function is a method of a class"""
    return_repr: str
    """The return type representation in template"""

    @property
    def input_args(self):
        return [arg for arg in self.args if arg.direction in ("IN", "INOUT")]

    @property
    def output(self):
        return [arg for arg in self.args if arg.direction in ("OUT", "INOUT")]

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

        # keep track of callbacks found during function argument parsing
        callback_found: list[GI.TypeInfo] = []
        """callbacks found during function argument parsing"""

        for arg in obj.get_arguments():
            direction: Literal["IN", "OUT", "INOUT"]
            if arg.get_direction() == GI.Direction.OUT:
                direction = "OUT"
            elif arg.get_direction() == GI.Direction.IN:
                direction = "IN"
            elif arg.get_direction() == GI.Direction.INOUT:
                direction = "INOUT"
            else:
                raise ValueError("Invalid direction")

            function_args.append(
                FunctionArgumentSchema.from_gi_object(
                    obj=arg,
                    direction=direction,
                )
            )
            # if any of the arguments is a callback, store it to be later parsed
            try:
                if gi_type_is_callback(arg.get_type()):
                    callback_found.append(arg.get_type())

            except AttributeError as e:
                # removed in pygobject 3.54.0?? was present in 3.50.0
                # logger.warning(
                #     f"Could not get gi type for argument {arg.get_name()}: {e}"
                # )
                gi_type_info = arg.get_type_info()
                if gi_type_is_callback(gi_type_info):
                    callback_found.append(gi_type_info)

        py_return_type = gi_type_to_py_type(obj.get_return_type())

        # get the repr of the return type
        py_return_type_namespace = get_py_type_namespace_repr(py_return_type)
        py_return_type_name = get_py_type_name_repr(py_return_type)

        namespace = obj.get_namespace()
        may_return_null = obj.may_return_null()
        is_callback = isinstance(obj, GI.CallbackInfo)

        # get the return repr for the template
        is_nullable = " | None" if may_return_null else ""
        return_repr = f"{py_return_type_name}{is_nullable}"

        # add namespace if it is different from the current namespace
        if py_return_type_namespace and py_return_type_namespace != namespace:
            return_repr = f"{py_return_type_namespace}.{return_repr}"

        return cls(
            namespace=namespace,
            name=obj.get_name(),
            args=function_args,
            is_callback=is_callback,
            docstring=docstring,
            may_return_null=may_return_null,
            is_method=obj.is_method(),
            can_throw_gerror=obj.can_throw_gerror(),
            is_deprecated=obj.is_deprecated(),
            skip_return=obj.skip_return(),
            return_repr=return_repr,
            _gi_callbacks=callback_found,
        )

    @property
    def debug(self):
        """
        Debug docstring
        """

        data = ""
        if self.docstring:
            data = f"{self.docstring}"

        return f"{data}\n[DEBUG]\n{self.model_dump_json(indent=2)}"


class ClassPropSchema(BaseSchema):
    name: str
    type: str
    is_deprecated: bool
    readable: bool
    writable: bool

    line_comment: str | None
    type_repr: str
    """type representation in template"""


class ClassSchema(BaseSchema):
    namespace: str
    name: str
    super: list[str]
    docstring: ClassDocs | None

    props: list[ClassPropSchema]
    attributes: list[VariableSchema]
    methods: list[FunctionSchema]
    extra: list[str]

    is_deprecated: bool

    @classmethod
    def from_gi_object(
        cls,
        namespace: str,
        obj: Any,
        docstring: ClassDocs | None,
        props: list[ClassPropSchema],
        attributes: list[VariableSchema],
        methods: list[FunctionSchema],
        extra: list[str],
    ):
        gi_info = None
        if hasattr(obj, "__info__"):
            gi_info = obj.__info__

        is_deprecated = gi_info.is_deprecated() if gi_info else False
        try:
            extra.extend(
                [
                    f"mro={obj.__mro__}",
                    # f"mro={obj.mro()}",
                    f"self={obj.__module__}.{obj.__name__}",
                ]
            )
        except Exception as e:
            breakpoint()

        return cls(
            namespace=namespace,
            name=obj.__name__,
            super=[get_super_class_name(obj, current_namespace=namespace)],
            docstring=docstring,
            props=props,
            attributes=attributes,
            methods=methods,
            is_deprecated=is_deprecated,
            extra=extra,
            # _gi_callbacks=gi_callbacks,
        )

    @property
    def debug(self):
        """
        Debug docstring
        """

        data = ""
        if self.docstring:
            data = f"{self.docstring}"

        return f"{data}\n[DEBUG]\n{self.model_dump_json(indent=2)}"


# class ClassSchema(BaseModel):
#     parents: list[str]
#     attributes: list[VariableSchema]
#     methods: list[FunctionSchema]

# capire se un method è statico
# capire se un method è di classe o di istanza
# cosa succede alle sotto classi? i.e Allocator.Props


class ModuleSchema(BaseSchema):
    name: str
    version: int = 1
    # attributes: list[Attribute]
    classes: list[ClassSchema]
    constant: list[VariableSchema]
    enum: list[EnumSchema]
    function: list[FunctionSchema]
    builtin_function: list[BuiltinFunctionSchema]
    used_callbacks: list[FunctionSchema]
    aliases: list[AliasSchema]

    def to_pyi(self, debug=False) -> str:
        """
        Return the module as a pyi file
        """
        import jinja2
        from gi_stub_generator.template import TEMPLATE

        environment = jinja2.Environment()
        output_template = environment.from_string(TEMPLATE)

        sanitized_module_name = sanitize_module_name(self.name)

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
        )
