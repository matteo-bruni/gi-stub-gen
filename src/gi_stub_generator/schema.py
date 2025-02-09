import keyword
from gi_stub_generator.utils import (
    gi_type_is_callback,
    gi_type_to_py_type,
    is_py_builtin_type,
)
from pydantic import BaseModel, PrivateAttr, computed_field


from typing import Any, Literal


class VariableSchema(BaseModel):
    namespace: (
        str  # need to be passed since it is not available in the python std types
    )
    name: str
    _gi_type: Any = PrivateAttr()  # actual type object
    value: Any | None = None

    @computed_field
    @property
    def type(self) -> str:
        return self._gi_type.__name__

    @computed_field
    @property
    def value_repr(self) -> str:
        # if self._gi_type in (int, str, float):
        if is_py_builtin_type(self._gi_type):
            return repr(self.value)

        # TODO: check the type if it is an enum/flag
        # TODO: enum/flags should have
        # CONSTANT_NAME: EnumType = EnumType(VALUE)
        # or
        # CONSTANT_NAME: EnumType = VALUE ???
        # return f"{self.value}"
        # return f"{self.parent}.{self._type.__name__}({self.value})"
        return f"{self._gi_type.__name__}({self.value})"

    def __init__(self, _gi_type, **data):
        super().__init__(**data)
        self._gi_type = _gi_type

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        if is_py_builtin_type(self._gi_type):
            return False
        if not hasattr(self._gi_type, "is_deprecated"):
            return False
        return self._gi_type.is_deprecated()

    def __str__(self):
        # print(self.value_repr, self.type)
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        return (
            f"namespace={self.namespace} "
            f"name={self.name} "
            f"type={self.type} "
            f"value={self.value} "
            f"value_repr={self.value_repr} {deprecated} "
            # f"mro={self._gi_type.mro()}"
        )


class EnumFieldSchema(BaseModel):
    @computed_field
    def name(self) -> int:
        return self._gi_info.get_name().upper()

    @computed_field
    def value(self) -> int:
        return self._gi_info.get_value()

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        return self._gi_info.is_deprecated()

    def __init__(self, _gi_info, **data):
        super().__init__(**data)
        self._gi_info = _gi_info

    def __str__(self):
        deprecated = "[DEPRECATED] " if self.is_deprecated else ""
        return f"name={self.name} value={self.value} {deprecated}"


class EnumSchema(BaseModel):
    _gi_type: Any
    enum_type: Literal["enum", "flags"]

    values: list[EnumFieldSchema]

    def py_super_type_str(self):
        """Return the python type as a string (otherwise capitalization is wrong)"""
        return "GObject.GFlags" if self.enum_type == "flags" else "GObject.GEnum"

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        return self._gi_info.is_deprecated()

    @property
    def _gi_info(self):
        return self._gi_type.__info__

    def __init__(self, _gi_type, **data):
        super().__init__(**data)
        self._gi_type = _gi_type

    @computed_field
    @property
    def namespace(self) -> str:
        return self._gi_info.get_namespace()

    @computed_field
    @property
    def name(self) -> str:
        return self._gi_info.get_name()

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        args_str = "\n".join([f"   - {arg}" for arg in self.values])
        mro = f"mro={self._gi_type.mro()}"
        return (
            f"{deprecated}namespace={self.namespace} name={self.name} {mro}\n{args_str}"
        )


class FunctionArgumentSchema(BaseModel):
    """gi.ArgInfo"""

    namespace: str
    name: str
    is_optional: bool
    direction: Literal["IN", "OUT", "INOUT"]
    _gi_type: Any

    @property
    def name_is_keyword(self):
        return keyword.iskeyword(self.name)

    @computed_field
    @property
    def is_callback(self) -> bool:
        return gi_type_is_callback(self._gi_type)

    # @computed_field
    @property
    def py_type(self):
        py_type = gi_type_to_py_type(self._gi_type)

        # if self._gi_type.get_tag() == GIRepository.TypeTag.INTERFACE and isinstance(
        #     self._gi_type.get_interface(), GIRepository.CallbackInfo
        # ):
        if gi_type_is_callback(self._gi_type):
            # TODO: registrare protocollo
            return f"Protocol({py_type})"
        # if isinstance(py_type, GIRepository.CallbackInfo):
        #     print(
        #         f"{self._gi_type.get_name()} py_type={py_type}, {self._gi_type.get_type()}"
        #     )
        #     print(f"{self._gi_type}")
        #     return py_type
        #     return self._gi_type.get_name()
        #     # TODO: crash su int perchè
        #     if self._gi_type.get_type().get_tag() == GIRepository.TypeTag.INTERFACE:
        #         # TODO: return Protocol typed since it is a virtual function
        #         raise ValueError("Callback not supported")

        return py_type

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        return self._gi_type.is_deprecated()

    @computed_field
    @property
    def tag_as_string(self) -> str:
        return self._gi_type.get_tag_as_string()

    @computed_field
    @property
    def get_array_length(self) -> int:
        return self._gi_type.get_array_length()

    def __init__(self, _gi_type, **data):
        super().__init__(**data)
        self._gi_type = _gi_type

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        return (
            f"name={self.name} [keyword={self.name_is_keyword}] {deprecated}"
            f"is_optional={self.is_optional} "
            # f"_gi_type={self._gi_type} "
            f"direction={self.direction} "
            f"py_type={self.py_type} "
            f"is_callback={self.is_callback} "
            f"tag_as_string={self.tag_as_string} "
            f"get_array_length={self.get_array_length} "
        )


class BuiltinFunctionSchema(BaseModel):
    name: str
    namespace: str
    signature: str
    docstring: str


class FunctionSchema(BaseModel):
    namespace: str
    name: str
    args: list[FunctionArgumentSchema]

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


class ClassPropSchema(BaseModel):
    name: str
    type: str
    is_deprecated: bool
    readable: bool
    writable: bool


class ClassSchema(BaseModel):
    namespace: str
    name: str
    super: list[str]

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


class Module(BaseModel):
    name: str
    version: int = 1
    # attributes: list[Attribute]
    classes: list[ClassSchema]
    constant: list[VariableSchema]
    enum: list[EnumSchema]
    function: list[FunctionSchema]
    builtin_function: list[BuiltinFunctionSchema]
    used_callbacks: list[FunctionSchema]
