import keyword
from gi_stub_generator.gir_parser import ClassDocs, FunctionDocs
from gi_stub_generator.utils import (
    gi_type_is_callback,
    gi_type_to_py_type,
    is_py_builtin_type,
)
from pydantic import BaseModel, ConfigDict, PrivateAttr, computed_field
import gi._gi as GI  # pyright: ignore[reportMissingImports]

from typing import Any, Literal


class BaseSchema(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class VariableSchema(BaseSchema):
    namespace: (
        str  # need to be passed since it is not available in the python std types
    )
    name: str
    value: Any | None

    is_deprecated: bool

    type_repr: str
    """type representation in template"""

    value_repr: str
    """value representation in template"""

    docstring: str | None

    @classmethod
    def from_gi_object(
        cls,
        obj,
        namespace: str,  # need to be passed since it is not available for python std types
        name: str,
        docstring: str | None,
    ):
        object_type = type(obj)
        object_type_namespace: str | None = None
        if hasattr(obj, "__info__"):
            if obj.__info__.get_namespace() != namespace:
                object_type_namespace = str(obj.__info__.get_namespace())

        # type representation in template should include namespace only if
        # it is different from the current namespace
        object_type_repr = object_type.__name__
        if object_type_namespace and object_type_namespace != namespace:
            object_type_repr = f"{object_type_namespace}.{object_type_repr}"

        # get value representation in template
        value_repr: str = ""
        if is_py_builtin_type(object_type):
            value_repr = repr(obj)

        elif hasattr(obj, "__info__"):
            # value is from gi: can be an enum or flags
            if type(obj.__info__) is GI.EnumInfo:
                is_flags = obj.__info__.is_flags()

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
        else:
            # Fallback to using the real value
            value_repr = f"{object_type_repr}({obj}) # TODO: not found ??"

        is_deprecated = False
        if hasattr(object_type, "is_deprecated"):
            is_deprecated = object_type.is_deprecated()

        return cls(
            namespace=namespace,
            name=name,
            type_repr=object_type_repr,
            value=obj,
            value_repr=value_repr,
            is_deprecated=is_deprecated,
            docstring=docstring,
        )

    model_config = ConfigDict(use_attribute_docstrings=True)

    def __str__(self):
        # print(self.value_repr, self.type)
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        return (
            f"namespace={self.namespace} "
            f"name={self.name} "
            f"type={type(self.value)} "
            f"value={self.value} "
            f"value_repr={self.value_repr} {deprecated} "
        )


class EnumFieldSchema(BaseSchema):
    name: str
    value: int
    value_repr: str
    """value representation in template"""

    is_deprecated: bool
    docstring: str | None = None

    @classmethod
    def from_gi_value_info(
        cls,
        value_info: GI.ValueInfo,
        docstring: str | None,
    ):
        return cls(
            name=value_info.get_name().upper(),
            value=value_info.get_value(),
            value_repr=repr(value_info.get_value()),
            is_deprecated=value_info.is_deprecated(),
            docstring=docstring,
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

    mro: list[str]
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
            mro=[f"{o.__module__}.{o.__name__}" for o in obj.mro()],
        )

    @computed_field
    @property
    def py_super_type_str(self) -> str:
        """Return the python type as a string (otherwise capitalization is wrong)"""
        return "GObject.GFlags" if self.enum_type == "flags" else "GObject.GEnum"

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        args_str = "\n".join([f"   - {arg}" for arg in self.fields])
        mro = f"mro={self.mro}"
        return (
            f"{deprecated}namespace={self.namespace} name={self.name} {mro}\n{args_str}"
        )


class FunctionArgumentSchema(BaseSchema):
    """gi.ArgInfo"""

    namespace: str
    name: str
    is_optional: bool
    direction: Literal["IN", "OUT", "INOUT"]
    _object: Any

    @property
    def _gi_type(self):
        return self._object.get_type()

    @property
    def name_is_keyword(self):
        return keyword.iskeyword(self.name)

    @computed_field
    @property
    def is_callback(self) -> bool:
        return gi_type_is_callback(self._gi_type)

    # @computed_field
    @property
    def py_type_namespace(self) -> str | None:
        if hasattr(self.py_type, "__info__"):
            return f"{self.py_type.__info__.get_namespace()}"  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
        from inspect import getmodule

        if str(self.py_type) == "Gst.Bin":
            breakpoint()
        if module_namespace := getmodule(self.py_type):
            name = module_namespace.__name__
            # manual fix for some modules, how to get the correct namespace?
            name = name.replace("gobject", "GObject")
            if name == "builtins":
                return None
            return name

        return None

    @property
    def type_repr(self):
        """
        type representation in template
        """
        # {% if a.py_type_namespace and a.py_type_name != module %}{{a.py_type_namespace}}.{% endif %}{{a.py_type_name}} {% if a.may_be_null %}| None {% endif %}

        is_nullable = " | None" if self.may_be_null else ""
        if self.py_type_namespace and self.py_type_namespace != self.namespace:
            return f"{self.py_type_namespace}.{self.py_type_name}{is_nullable}"
        return f"{self.py_type_name}{is_nullable}"

    @property
    def py_type_name(self):
        if gi_type_is_callback(self._gi_type):
            # TODO: registrare protocollo
            return f"TODOProtocol({self.py_type})"

        if hasattr(self.py_type, "__info__"):
            return f"{self.py_type.__info__.get_name()}"  # type: ignore

        if hasattr(self.py_type, "__name__"):
            return self.py_type.__name__  # type: ignore

        return self.py_type

    @property
    def py_type(self):
        py_type = gi_type_to_py_type(self._gi_type)

        # if gi_type_is_callback(self._gi_type):
        #     # TODO: registrare protocollo
        #     return f"Protocol({py_type})"

        return py_type
        if hasattr(py_type, "__info__"):
            return f"{py_type.__info__.get_namespace()}.{py_type.__info__.get_name()}"

        if hasattr(py_type, "__name__"):
            return py_type.__name__

        return py_type

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        return self._gi_type.is_deprecated()

    @computed_field
    @property
    def may_be_null(self) -> bool:
        return self._object.may_be_null()

    @computed_field
    @property
    def tag_as_string(self) -> str:
        return self._gi_type.get_tag_as_string()

    @computed_field
    @property
    def get_array_length(self) -> int:
        return self._gi_type.get_array_length()

    def __init__(self, _object, **data):
        super().__init__(**data)
        self._object = _object

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        return (
            f"name={self.name} [keyword={self.name_is_keyword}] {deprecated}"
            f"is_optional={self.is_optional} "
            f"may_be_null={self.may_be_null} "
            # f"_gi_type={self._gi_type} "
            f"direction={self.direction} "
            f"py_type={self.py_type} "
            f"is_callback={self.is_callback} "
            f"tag_as_string={self.tag_as_string} "
            f"get_array_length={self.get_array_length} "
        )


class BuiltinFunctionSchema(BaseSchema):
    name: str
    namespace: str
    signature: str
    docstring: str


class FunctionSchema(BaseSchema):
    namespace: str
    name: str
    args: list[FunctionArgumentSchema]
    docstring: FunctionDocs | None

    is_callback: bool
    """Whether this function is a callback"""

    _gi_type: Any
    _gi_callbacks: list[Any]

    @computed_field
    @property
    def can_throw_gerror(self) -> bool:
        return self._gi_type.can_throw_gerror()

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        return self._gi_type.is_deprecated()

    @computed_field
    @property
    def skip_return(self) -> bool:
        return self._gi_type.skip_return()

    @computed_field
    @property
    def may_return_null(self) -> bool:
        return self._gi_type.may_return_null()

    @computed_field
    @property
    def is_method(self) -> bool:
        if self.is_callback:
            return False
        return self._gi_type.is_method()

    @property
    def py_return_type(self):
        return gi_type_to_py_type(self._gi_type.get_return_type())

    @property
    def py_return_type_namespace(self) -> str | None:
        if hasattr(self.py_return_type, "__info__"):
            return f"{self.py_return_type.__info__.get_namespace()}"  # type: ignore
        return None

    @property
    def py_return_type_name(self):
        if hasattr(self.py_return_type, "__info__"):
            return f"{self.py_return_type.__info__.get_name()}"  # type: ignore

        if hasattr(self.py_return_type, "__name__"):
            return self.py_return_type.__name__  # type: ignore

        return self.py_return_type

    @property
    def return_repr(self):
        """
        type representation in template
        """
        # {% if a.py_type_namespace and a.py_type_name != module %}{{a.py_type_namespace}}.{% endif %}{{a.py_type_name}} {% if a.may_be_null %}| None {% endif %}

        is_nullable = " | None" if self.may_return_null else ""
        if (
            self.py_return_type_namespace
            and self.py_return_type_namespace != self.namespace
        ):
            return f"{self.py_return_type_namespace}.{self.py_return_type_name}{is_nullable}"
        return f"{self.py_return_type_name}{is_nullable}"

    # @property
    # def return_repr(self):
    #     """
    #     type representation in template
    #     """

    #     nullable = " | None" if self.may_return_null else ""
    #     return_types: list[str] = [f"{self.py_return_type}{nullable}"]
    #     for arg in self.output:
    #         return_types.append(arg.type_repr)

    #     return ", ".join(return_types)

    @property
    def input_args(self):
        return [arg for arg in self.args if arg.direction in ("IN", "INOUT")]

    @property
    def output(self):
        return [arg for arg in self.args if arg.direction in ("OUT", "INOUT")]

    def __init__(
        self,
        _gi_type,
        _gi_callbacks,
        **data,
    ):
        super().__init__(**data)
        self._gi_type = _gi_type
        self._gi_callbacks = _gi_callbacks

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        can_throw_gerror = (
            "can_throw_gerror=True"
            if self.can_throw_gerror
            else "can_throw_gerror=False"
        )
        input_args = "\n".join([f"   - {arg}" for arg in self.input_args])
        callback_str = "[CallbackInfo]" if self.is_callback else "[FunctionInfo]"
        output_args = [f"   - {self.py_return_type} nullable={self.may_return_null}"]
        output_args.extend([f"   - {arg}" for arg in self.output])
        output_args = "\n".join(output_args)
        return (
            f"{self.namespace}.{self.name} {callback_str} {deprecated}\n"
            f"  namespace={self.namespace} name={self.name} is_method={self.is_method} {can_throw_gerror}\n"
            f"  return_type={self.py_return_type} get_array_length={self._gi_type.get_return_type().get_array_length()} may_return_null={self.may_return_null} skip_return={self.skip_return}\n"
            f"  Input Args:\n"
            f"{input_args}\n"
            f"  Output Args:\n"
            f"{output_args}\n"
        )


class ClassPropSchema(BaseSchema):
    name: str
    type: str
    is_deprecated: bool
    readable: bool
    writable: bool


class ClassSchema(BaseSchema):
    namespace: str
    name: str
    super: list[str]
    docstring: ClassDocs | None

    props: list[ClassPropSchema]
    attributes: list[VariableSchema]
    methods: list[FunctionSchema]
    extra: list[str]

    _gi_callbacks: list[Any]

    def __init__(self, _gi_type, _gi_callbacks, **data):
        super().__init__(**data)
        self._gi_type = _gi_type
        self._gi_callbacks = _gi_callbacks

    @property
    def _gi_info(self):
        if hasattr(self._gi_type, "__info__"):
            return self._gi_type.__info__
        return None

    @property
    def is_deprecated(self):
        if self._gi_info:
            return self._gi_info.is_deprecated()
        return False

    def __str__(self):
        attributes_str = "\n".join([f"   - {a}" for a in self.attributes])
        # methods_str = "\n".join([f"   - {m}" for m in self.methods])
        methods_str = "\n".join([f"   - {m.name}" for m in self.methods])
        extra_str = "\n".join([f"   - {e}" for e in self.extra])
        props_str = "\n".join([f"   - {p}" for p in self.props])
        return (
            f"Class {self.name}({self.super})\n"
            f"\t Props: \n{props_str}\n"
            f"\t Attributes: \n{attributes_str}\n"
            f"\t Methods: \n{methods_str}\n"
            f"\t Extra: \n{extra_str}\n"
        )


# class ClassSchema(BaseModel):
#     parents: list[str]
#     attributes: list[VariableSchema]
#     methods: list[FunctionSchema]

# capire se un method è statico
# capire se un method è di classe o di istanza
# cosa succede alle sotto classi? i.e Allocator.Props


class Module(BaseSchema):
    name: str
    version: int = 1
    # attributes: list[Attribute]
    classes: list[ClassSchema]
    constant: list[VariableSchema]
    enum: list[EnumSchema]
    function: list[FunctionSchema]
    builtin_function: list[BuiltinFunctionSchema]
    used_callbacks: list[FunctionSchema]
