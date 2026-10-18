"""Curated internal PyGObject API, checked with 3.58.1.

C descriptors have no inspect.Signature. Keep declarations here, not in generated
stubs; validate member presence against gi._gi on every generation. This is not
an alias for the public GIRepository API. Extend only for actual consumers.
"""

# Values are Python signatures, parsed into the existing callable models.
INFO_METHODS: dict[str, tuple[str, ...]] = {
    "BaseInfo": (
        "equal(self, other: BaseInfo, /) -> bool",
        "get_name(self) -> str | None",
        "get_name_unescaped(self) -> str | None",
        "get_namespace(self) -> str",
        "get_container(self) -> BaseInfo | None",
        "get_attribute(self, name: str, /) -> str | None",
        "is_deprecated(self) -> bool",
    ),
    "ArgInfo": (
        "get_type_info(self) -> TypeInfo",
        "get_direction(self) -> int",
        "get_closure_index(self) -> int",
        "get_destroy_index(self) -> int",
        "get_scope(self) -> int",
        "get_ownership_transfer(self) -> int",
        "is_optional(self) -> bool",
        "may_be_null(self) -> bool",
        "is_caller_allocates(self) -> bool",
        "is_return_value(self) -> bool",
    ),
    "TypeInfo": (
        "get_tag(self) -> int",
        "get_tag_as_string(self) -> str",
        "get_interface(self) -> BaseInfo | None",
        "get_param_type(self, index: int, /) -> TypeInfo | None",
        "get_array_length_index(self) -> int",
        "get_array_fixed_size(self) -> int",
        "get_array_type(self) -> int",
        "is_zero_terminated(self) -> bool",
        "is_pointer(self) -> bool",
    ),
    "CallableInfo": (
        "get_arguments(self) -> tuple[ArgInfo, ...]",
        "get_return_type(self) -> TypeInfo",
        "get_caller_owns(self) -> int",
        "can_throw_gerror(self) -> bool",
        "may_return_null(self) -> bool",
        "skip_return(self) -> bool",
    ),
    "FunctionInfo": (
        "get_flags(self) -> int",
        "get_symbol(self) -> str",
        "is_method(self) -> bool",
        "get_finish_func(self) -> FunctionInfo | None",
        "__call__(self, *args: object, **kwargs: object) -> typing.Any",
    ),
    "CallbackInfo": (),
    "SignalInfo": ("get_flags(self) -> int", "true_stops_emit(self) -> bool"),
    "VFuncInfo": ("get_flags(self) -> int", "get_offset(self) -> int", "get_invoker(self) -> FunctionInfo | None"),
    "RegisteredTypeInfo": (
        "get_g_type(self) -> GObject.GType",
        "get_type_name(self) -> str | None",
        "get_type_init(self) -> str | None",
    ),
    "ObjectInfo": (
        "get_parent(self) -> ObjectInfo | None",
        "get_interfaces(self) -> tuple[InterfaceInfo, ...]",
        "get_methods(self) -> tuple[FunctionInfo, ...]",
        "get_fields(self) -> tuple[FieldInfo, ...]",
        "get_properties(self) -> tuple[PropertyInfo, ...]",
        "get_signals(self) -> tuple[SignalInfo, ...]",
        "get_vfuncs(self) -> tuple[VFuncInfo, ...]",
        "get_constants(self) -> tuple[ConstantInfo, ...]",
        "get_abstract(self) -> bool",
        "get_fundamental(self) -> bool",
    ),
    "InterfaceInfo": (
        "get_methods(self) -> tuple[FunctionInfo, ...]",
        "get_properties(self) -> tuple[PropertyInfo, ...]",
        "get_signals(self) -> tuple[SignalInfo, ...]",
        "get_vfuncs(self) -> tuple[VFuncInfo, ...]",
        "get_constants(self) -> tuple[ConstantInfo, ...]",
        "get_prerequisites(self) -> tuple[BaseInfo, ...]",
    ),
    "StructInfo": (
        "get_methods(self) -> tuple[FunctionInfo, ...]",
        "get_fields(self) -> tuple[FieldInfo, ...]",
        "get_size(self) -> int",
        "is_gtype_struct(self) -> bool",
        "is_foreign(self) -> bool",
    ),
    "UnionInfo": (
        "get_methods(self) -> tuple[FunctionInfo, ...]",
        "get_fields(self) -> tuple[FieldInfo, ...]",
        "get_size(self) -> int",
    ),
    "EnumInfo": (
        "is_flags(self) -> bool",
        "get_values(self) -> tuple[ValueInfo, ...]",
        "get_methods(self) -> tuple[FunctionInfo, ...]",
        "get_storage_type(self) -> int",
    ),
    "ValueInfo": ("get_value(self) -> int",),
    "ConstantInfo": ("get_value(self) -> object",),
    "FieldInfo": (
        "get_type_info(self) -> TypeInfo",
        "get_flags(self) -> int",
        "get_size(self) -> int",
        "get_offset(self) -> int",
    ),
    "PropertyInfo": (
        "get_type_info(self) -> TypeInfo",
        "get_flags(self) -> int",
        "get_ownership_transfer(self) -> int",
    ),
    "UnresolvedInfo": (),
}

OTHER_METHODS: dict[str, tuple[str, ...]] = {
    "Repository": (
        "@get_default() -> Repository",
        "require(self, namespace: str, version: str | None = None, lazy: bool = False) -> None",
        "find_by_name(self, namespace: str, name: str) -> BaseInfo | None",
        "get_infos(self, namespace: str) -> tuple[BaseInfo, ...]",
        "get_version(self, namespace: str) -> str",
        "get_loaded_namespaces(self) -> list[str]",
        "get_dependencies(self, namespace: str) -> list[str]",
        "get_immediate_dependencies(self, namespace: str) -> list[str]",
        "enumerate_versions(self, namespace: str) -> list[str]",
        "is_registered(self, namespace: str, version: str | None = None) -> bool",
    ),
    "Async": (
        "__init__(self, finish_func: CallableInfo, cancellable: Gio.Cancellable = ...) -> None",
        "__await__(self) -> typing.Generator[Async[T], None, T]",
        "result(self) -> T",
        "done(self) -> bool",
        "exception(self) -> BaseException | None",
        "cancel(self, msg: str | None = None) -> None",
        "add_done_callback(self, callback: typing.Callable[[Async[T]], object], /, *, context: contextvars.Context | None = None) -> None",
        "remove_done_callback(self, callback: typing.Callable[[Async[T]], object], /) -> int",
    ),
}

FLAG_CLASSES = (
    "TypeTag",
    "Direction",
    "Transfer",
    "ScopeType",
    "ArrayType",
    "FunctionInfoFlags",
    "FieldInfoFlags",
    "VFuncInfoFlags",
)
FUNCTIONS = (
    "enum_add(gtype: GObject.GType, /) -> type[GObject.GEnum]",
    "flags_add(gtype: GObject.GType, /) -> type[GObject.GFlags]",
)
