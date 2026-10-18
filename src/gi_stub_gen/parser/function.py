from __future__ import annotations

import logging
from typing import Any

import gi._gi as GI
from gi_stub_gen.schema.function import FunctionSchema, FunctionArgumentSchema, CallbackSchema
from gi_stub_gen.adapter import GIRepositoryCallableAdapter
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.parser.gir import GirTypeMetadata
from gi_stub_gen.utils.gi_utils import (
    catch_gi_deprecation_warnings,
    get_gi_type_info,
    get_safe_gi_arg_closure_index,
    get_safe_gi_array_length,
    get_safe_gi_destroy_index,
    gi_type_is_callback,
    gi_type_to_py_type,
)
from gi_stub_gen.utils.utils import sanitize_variable_name
from gi_stub_gen.utils.inspect_utils import _extract_annotation_type_info
from gi.repository import GIRepository
from typing import Literal
import re

logger = logging.getLogger(__name__)


KNOWN_UNSUPPORTED_GI_FUNCTIONS = {
    ("GObject", "signal_set_va_marshaller"): "VaClosureMarshal is marked introspectable=0 in the GIR",
}


def parse_function(
    attribute: Any,
    docstring: str | None,
    docs: GIRDocs | None = None,
    render_namespace: str | None = None,
) -> FunctionSchema | None:
    """Parse supported GI functions; docs=None disables GIR metadata lookup."""
    is_function = isinstance(attribute, GI.FunctionInfo)
    if not is_function:
        return None

    # this has happened in i.repository.GstVideo.VideoChromaResample
    # there is a function with an empty name ???
    function_name = attribute.get_name()
    if not function_name:
        logger.error("Found function with an empty name!?!, skipping...")
        return None

    function_key = (attribute.get_namespace(), function_name)
    if function_key in KNOWN_UNSUPPORTED_GI_FUNCTIONS:
        logger.warning(
            "Skipping %s.%s: %s",
            function_key[0],
            function_key[1],
            KNOWN_UNSUPPORTED_GI_FUNCTIONS[function_key],
        )
        return None

    return parse_callable(obj=attribute, docstring=docstring, docs=docs, render_namespace=render_namespace)


def _is_gvalue_type(gir_type: GirTypeMetadata | None) -> bool:
    if gir_type is None or gir_type.c_type is None:
        return False
    c_types = (gir_type.c_type, gir_type.element_c_type or "")
    return any(re.search(r"\bGValue\b", c_type) for c_type in c_types)


def _ownership_is_transferred(gir_type: GirTypeMetadata) -> bool:
    return gir_type.transfer_ownership not in (None, "none")


def _is_marshaled_gvalue_argument(
    gir_type: GirTypeMetadata | None,
    direction: Literal["IN", "OUT", "INOUT"],
    callable_type: str,
) -> bool:
    """Classify GValues that PyGObject exposes as their unpacked payload."""
    if not _is_gvalue_type(gir_type):
        return False
    assert gir_type is not None

    if callable_type in ("CallbackInfo", "SignalInfo"):
        return True
    if direction == "OUT":
        return True
    c_type = gir_type.c_type
    return (c_type is not None and "const" in c_type) or _ownership_is_transferred(gir_type)


def _is_marshaled_gvalue_return(
    gir_type: GirTypeMetadata | None,
    callable_type: str,
) -> bool:
    if not _is_gvalue_type(gir_type):
        return False
    assert gir_type is not None
    c_type = gir_type.c_type
    return (
        callable_type in ("CallbackInfo", "SignalInfo")
        or (c_type is not None and "const" in c_type)
        or _ownership_is_transferred(gir_type)
    )


def parse_argument(
    obj: GI.ArgInfo | GIRepositoryCallableAdapter,
    direction: Literal["IN", "OUT", "INOUT"],
    variadic: bool = False,  # i.e in case of (*args) -> (arg0, arg1, ...)
    gir_type: GirTypeMetadata | None = None,
    callable_type: str = "FunctionInfo",
    docs: GIRDocs | None = None,
    render_namespace: str | None = None,
) -> tuple[FunctionArgumentSchema, CallbackSchema | None]:
    """Construct an argument and its optional callback with the same document context."""
    found_callback: CallbackSchema | None = None

    container = obj.get_container()
    assert container is not None, "Argument has no callable container"
    function_namespace: str = container.get_namespace()
    annotation_namespace = render_namespace or function_namespace
    argument_namespace: str = obj.get_namespace()
    argument_name = obj.get_name()
    assert argument_name is not None, "Argument name is None"

    gi_type = get_gi_type_info(obj)
    assert isinstance(gi_type, (GI.TypeInfo, GIRepositoryCallableAdapter))
    type_hint_namespace: str | None
    type_hint_name: str
    type_hint_comment: str | None = None
    type_imports: set[str] = set()

    # if is a callback, we record its return type for type hinting
    # to create something like arg: Callback | typing.Callable[..., PadProbeReturn]
    type_hint_cb_return_name = None
    type_hint_cb_return_namespace = None

    is_callback = gi_type_is_callback(gi_type)

    # callback cant be instantiated directly to python objects
    # so we need to get the interface and create a CallbackSchema
    if is_callback:
        # Get the interface (The actual CallbackInfo)
        cb_info = gi_type.get_interface()
        assert isinstance(cb_info, (GI.CallbackInfo, GIRepositoryCallableAdapter)), "Invalid callback interface"

        cb_name = cb_info.get_name()
        assert cb_name is not None, "CallbackInfo has no name"

        cb_namespace = cb_info.get_namespace()

        # we found all the info to create the type hint
        type_hint_namespace = cb_namespace
        type_hint_name = cb_name

        # retrieve the cb return type
        cb_schema = parse_callable(cb_info, docs=docs, render_namespace=annotation_namespace)
        type_hint_cb_return_name = cb_schema.return_hint
        type_hint_cb_return_namespace = cb_schema.return_hint_namespace
        type_imports.update(cb_schema.return_type_imports)
        if type_hint_cb_return_namespace:
            type_imports.add(type_hint_cb_return_namespace)

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
            found_callback = CallbackSchema(
                name=cb_name,
                function=cb_schema,
            )
            # TODO: callback can have callback as param? handle that case
            # cb_schema._gi_callbacks <- extend with found_callback and return list?

    else:
        # Standard type logic
        # we can get the python type from the gi type
        py_type = gi_type_to_py_type(gi_type)
        type_hint_name, type_hint_namespace = _extract_annotation_type_info(
            py_type,
            current_namespace=annotation_namespace,
            required_imports=type_imports,
        )

    array_length: int = get_safe_gi_array_length(gi_type)
    is_caller_allocates = obj.is_caller_allocates()
    is_marshaled_gvalue_payload = _is_marshaled_gvalue_argument(
        gir_type,
        direction,
        callable_type,
    )
    if is_marshaled_gvalue_payload:
        type_imports.clear()
        if gir_type is not None and gir_type.is_array:
            type_hint_name = "list[typing.Any]"
            type_hint_namespace = None
        else:
            type_hint_name = "Any"
            type_hint_namespace = "typing"

    return FunctionArgumentSchema(
        namespace=argument_namespace,
        name=argument_name,
        is_callback=is_callback,
        is_optional=obj.is_optional(),
        may_be_null=obj.may_be_null(),
        direction=direction,
        py_type_namespace=type_hint_namespace,
        py_type_name=type_hint_name,
        type_imports=type_imports,
        is_deprecated=gi_type.is_deprecated(),
        tag_as_string=gi_type.get_tag_as_string(),
        get_array_length=array_length,
        line_comment=type_hint_comment,
        is_caller_allocates=is_caller_allocates,
        default_value=None,
        is_pointer=gi_type.is_pointer(),
        is_variadic=variadic,
        type_hint_cb_return_name=type_hint_cb_return_name,
        type_hint_cb_return_namespace=type_hint_cb_return_namespace,
        is_marshaled_gvalue_payload=is_marshaled_gvalue_payload,
    ), found_callback


def parse_callable(
    obj: GI.FunctionInfo | GI.CallbackInfo | GI.SignalInfo | GIRepositoryCallableAdapter,
    docstring: str | None = None,
    docs: GIRDocs | None = None,
    render_namespace: str | None = None,
    include_async: bool = True,
) -> FunctionSchema:
    """Construct a callable, qualifying nested types for its destination module when supplied."""
    function_type: str
    if isinstance(obj, GI.SignalInfo):
        function_type = "SignalInfo"
    elif isinstance(obj, GI.CallbackInfo):
        function_type = "CallbackInfo"
    elif isinstance(obj, GI.VFuncInfo):
        raise NotImplementedError("VFuncInfo parsing not implemented yet. Please open issue with an example.")
    elif isinstance(obj, GI.FunctionInfo):
        function_type = "FunctionInfo"
    elif isinstance(obj, GIRepositoryCallableAdapter):
        function_type = obj.callable_type
    else:
        raise ValueError(f"Not a valid GI function or callback object or signal. Got: {type(obj)}")

    raw_function_name = obj.get_name()
    assert raw_function_name is not None, "Function name is None"
    container = obj.get_container()
    container_name = container.get_name() if container is not None else None

    gir_callable = (
        docs.get_callable_metadata(
            raw_function_name,
            container_name,
            function_type,
        )
        if docs is not None
        else None
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
    closure_indices = set()
    for i, arg in enumerate(obj_arguments):
        arg_type = get_gi_type_info(arg)
        array_length: int = get_safe_gi_array_length(arg_type)
        if array_length >= 0:
            indices_to_skip.add(array_length)

        # ask to this arg if another arg is its destroy notifier
        # WARNING!! in GIRepository.ArgInfo this returns a (bool, int)
        # while in pygobject GI.ArgInfo it returns just the int
        destroy_idx = get_safe_gi_destroy_index(arg)
        if destroy_idx >= 0:
            indices_to_skip.add(destroy_idx)

        # get closure indices
        closure_idx = get_safe_gi_arg_closure_index(arg)
        if closure_idx >= 0:
            closure_indices.add(closure_idx)

    # only the last closure index is variadic
    last_closure_index = max(closure_indices) if closure_indices else -1
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

        is_variadic = i == last_closure_index
        arg_name = arg.get_name()
        # IMPORTANT: For standard Function Stubs, arguments marked as 'OUT'
        # are NOT part of the Python input signature. They are returned in the tuple.
        # However, 'INOUT' arguments ARE passed as input (and returned modified).
        function_arg, found_callback = parse_argument(
            obj=arg,
            direction=direction,
            variadic=is_variadic,
            gir_type=gir_callable.param_types.get(arg_name)
            if gir_callable is not None and arg_name is not None
            else None,
            callable_type=function_type,
            docs=docs,
            render_namespace=render_namespace,
        )

        function_args.append(function_arg)
        if found_callback:
            # Found a callback argument
            # append to its originated_from info
            found_callback.originated_from = {f"{obj.get_namespace()}.{obj.get_name()}"}
            args_as_callbacks_found.append(found_callback)
            args_as_callbacks_found.extend(found_callback.function._gi_callbacks)

    function_namespace: str = obj.get_namespace()

    f_name = raw_function_name
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
    # is_callback = isinstance(obj, GI.CallbackInfo)
    is_callback = function_type == "CallbackInfo"

    # Callbacks do not have these flags
    is_constructor = False
    is_getter = False
    is_setter = False
    is_async = False
    wrap_vfunc = False
    is_method = getattr(obj, "is_method", lambda: False)()  # SignalInfo has no is_method()

    if function_type == "FunctionInfo":
        flags = obj.get_flags()  # type: ignore
        is_constructor = bool(flags & GIRepository.FunctionInfoFlags.IS_CONSTRUCTOR)
        is_getter = bool(flags & GIRepository.FunctionInfoFlags.IS_GETTER)
        is_setter = bool(flags & GIRepository.FunctionInfoFlags.IS_SETTER)
        # depending on glib version this may not be available,
        # so we check if the flag exists
        try:
            is_async = bool(flags & GIRepository.FunctionInfoFlags.IS_ASYNC)  # type: ignore
        except AttributeError:
            is_async = False
        wrap_vfunc = bool(flags & GIRepository.FunctionInfoFlags.WRAPS_VFUNC)

    # Return type hint logic
    line_comment: str | None = None
    return_type_imports: set[str] = set()
    if is_constructor and not is_callback:
        # if it is a constructor, the return type is the class itself
        # this happens in new() functions which in reality are static methods
        # that are polymorphic: e.g. Gst.Pipeline.new() -> Gst.Pipeline in python
        # but in C: GstElement* gst_pipeline_new (const gchar *name);
        # in C it is fine due to polimorphism, but with PyGObject this correctly
        # returns the actual class type.
        # we need to get the container
        # NOTE: we are going to set it as a @classmethod (see decorators property)
        # since in python constructors are classmethods
        # but in reality it should be @staticmethod
        # but there are some new() functions that are actually methods like GObject.new()
        # so for simplicity we set all constructors as classmethods
        class_container = obj.get_container()
        assert class_container is not None, "Function container is None for constructor"
        py_return_hint_namespace = class_container.get_namespace()
        py_return_hint_name = class_container.get_name()
    else:
        py_return_type = gi_type_to_py_type(obj.get_return_type())
        if py_return_type is None:
            py_return_hint_namespace = None
            py_return_hint_name = None
        else:
            # get the repr of the return type
            py_return_hint_name, py_return_hint_namespace = _extract_annotation_type_info(
                py_return_type,
                current_namespace=render_namespace or function_namespace,
                required_imports=return_type_imports,
            )

        if py_return_hint_namespace and py_return_hint_namespace.startswith("gi._"):
            line_comment = "type: ignore"

        gir_return_type = gir_callable.return_type if gir_callable is not None else None
        if _is_marshaled_gvalue_return(gir_return_type, function_type):
            return_type_imports.clear()
            return_type = gir_return_type
            assert return_type is not None
            if return_type.is_array:
                py_return_hint_name = "list[typing.Any]"
                py_return_hint_namespace = None
            else:
                py_return_hint_name = "Any"
                py_return_hint_namespace = "typing"

    to_return = FunctionSchema(
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
        return_hint=py_return_hint_name,
        return_hint_namespace=py_return_hint_namespace,
        return_type_imports=return_type_imports,
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
    from gi_stub_gen.parser.callback import specialize_callback

    specialize_callback(to_return, container_name)
    if include_async and isinstance(obj, GI.FunctionInfo):
        from gi_stub_gen.parser.async_ import add_async_overloads

        add_async_overloads(obj, to_return, docs)
    return to_return
