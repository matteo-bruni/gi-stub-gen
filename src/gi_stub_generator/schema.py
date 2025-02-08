import keyword
from gi_stub_generator.utils import gi_type_is_callback, gi_type_to_py_type
from pydantic import BaseModel, PrivateAttr
import gi._gi as GIRepository  # type: ignore


from typing import Any, Literal


class Constant(BaseModel):
    parent: str
    name: str
    _type: Any = PrivateAttr()  # actual type object
    value: Any | None = None

    @property
    def type(self):
        return self._type.__name__

    @property
    def value_repr(self):
        if self._type in (int, str, float):
            return repr(self.value)

        # TODO: enum/flags should have
        # CONSTANT_NAME: EnumType = EnumType(VALUE)
        # or
        # CONSTANT_NAME: EnumType = VALUE ???
        # return f"{self.value}"
        # return f"{self.parent}.{self._type.__name__}({self.value})"
        return f"{self._type.__name__}({self.value})"

    def __init__(self, _type, **data):
        super().__init__(**data)
        self._type = _type

    def __str__(self):
        return (
            f"parent={self.parent} "
            f"name={self.name} "
            f"type={self.type} "
            f"value={self.value} "
            f"value_repr={self.value_repr}"
        )


# class CallbackSchema(BaseModel):
#     _gi_type: Any
#     name: str
#     namespace: str

#     def __init__(self, _gi_type, **data):
#         super().__init__(**data)

#         if not gi_type_is_callback(_gi_type):
#             raise ValueError("Not a callback")
#         self._gi_type = _gi_type

# @property
# def namespace(self):
#     return self._gi_type.get_interface().get_namespace()

# @property
# def name(self):
#     return self._gi_type.get_interface().get_name()


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

    @property
    def tag_as_string(self):
        return self._gi_type.get_tag_as_string()

    @property
    def get_array_length(self):
        return self._gi_type.get_array_length()

    def __init__(self, _gi_type, **data):
        super().__init__(**data)
        self._gi_type = _gi_type

    def __str__(self):
        return (
            f"name={self.name} [keyword={self.name_is_keyword}] "
            f"is_optional={self.is_optional} "
            # f"_gi_type={self._gi_type} "
            f"direction={self.direction} "
            f"py_type={self.py_type} "
            f"tag_as_string={self.tag_as_string} "
            f"get_array_length={self.get_array_length}"
        )


class FunctionSchema(BaseModel):
    namespace: str
    name: str
    args: list[FunctionArgumentSchema]

    is_callback: bool
    """Whether this function is a callback"""

    _gi_type: Any
    _gi_callbacks: list[Any]

    @property
    def skip_return(self) -> bool:
        return self._gi_type.skip_return()

    @property
    def may_return_null(self) -> bool:
        return self._gi_type.may_return_null()

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
        input_args = "\n".join([f"   - {arg}" for arg in self.input_args])
        callback_str = "[CallbackInfo]" if self.is_callback else "[FunctionInfo]"
        output_args = [f"   - {self.py_return_type} nullable={self.may_return_null}"]
        output_args.extend([f"   - {arg}" for arg in self.output])
        output_args = "\n".join(output_args)
        return (
            f"{self.namespace}.{self.name} {callback_str}\n"
            f"  namespace={self.namespace} name={self.name} is_method={self.is_method} \n"
            f"  return_type={self.py_return_type} get_array_length={self._gi_type.get_return_type().get_array_length()} may_return_null={self.may_return_null} skip_return={self.skip_return}\n"
            f"  Input Args:\n"
            f"{input_args}\n"
            f"  Output Args:\n"
            f"{output_args}\n"
        )


class ClassSchema(BaseModel):
    parents: list[str]
    attributes: list[Constant]
    methods: list[FunctionSchema]

    # capire se un method è statico
    # capire se un method è di classe o di istanza
    # cosa succede alle sotto classi? i.e Allocator.Props


class Module(BaseModel):
    name: str
    version: int = 1
    # attributes: list[Attribute]
    constant: list[Constant]
    # enum: list[Attribute]
    function: list[FunctionSchema]
    used_callbacks: list[FunctionSchema]
