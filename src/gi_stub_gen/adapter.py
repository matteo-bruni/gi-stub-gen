from __future__ import annotations

from gi.repository import GIRepository
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi_stub_gen.schema.function import CallbackSchema


def get_callback_schema(namespace: str, callback_name: str) -> CallbackSchema:
    from gi_stub_gen.manager.gi_repo import GIRepo
    from gi_stub_gen.schema.function import FunctionSchema, CallbackSchema

    repo = GIRepo()
    pygobject_adapter = repo.find_callable(
        namespace,
        callback_name,
        namespace_version="2.0",
    )
    if pygobject_adapter is None:
        raise RuntimeError(f"Could not find {callback_name}")

    return CallbackSchema(
        function=FunctionSchema.from_gi_object(
            obj=pygobject_adapter,
            docstring=None,
        ),
        originated_from={"Manual from GIRepository"},
        name=callback_name,
    )


class GIRepositoryCallableAdapter:
    """
    Adapter for GIRepository callable infos (functions, methods, callbacks).
    Wraps a GIRepository.BaseInfo object and provides methods to access its properties.

    This way we can use the result of GIRepository calls without worrying about
    missing overrides usually done by pygobject.
    """

    def __init__(self, raw_info, parent=None):
        self._raw = raw_info
        self._parent = parent

    def get_container(self):
        if self._parent:
            return self._parent

        raw_container = getattr(self._raw, "get_container", lambda: None)()
        if raw_container:
            return GIRepositoryCallableAdapter(raw_container)
        return None

    def get_arguments(self):
        if not hasattr(self._raw, "get_n_args"):
            return []

        args = []
        for i in range(self._raw.get_n_args()):
            raw_arg = self._raw.get_arg(i)
            args.append(GIRepositoryCallableAdapter(raw_arg))
        return args

    def get_type(self):
        raw_type = None
        if hasattr(self._raw, "get_type_info"):  # pygobject v3.0
            raw_type = self._raw.get_type_info()
        elif hasattr(self._raw, "get_type"):  # pygobjectv2.0
            raw_type = self._raw.get_type()
        elif hasattr(self._raw, "get_tag"):
            return self

        if raw_type:
            return GIRepositoryCallableAdapter(raw_type, parent=self)

        raise AttributeError(f"Oggetto '{self._raw}' non ha metodi type.")

    def get_interface(self):
        """
        Intercetta type_info.get_interface() per continuare la catena.
        """
        raw_iface = self._raw.get_interface()
        return GIRepositoryCallableAdapter(raw_iface) if raw_iface else None

    def get_param_type(self, index):
        """
        Intercetta type_info.get_param_type(n) (per array/liste).
        """
        raw_param = self._raw.get_param_type(index)
        return GIRepositoryCallableAdapter(raw_param) if raw_param else None

    def get_tag_as_string(self):
        if not hasattr(self._raw, "get_tag"):
            return "unknown"

        tag = self._raw.get_tag()
        return GIRepository.type_tag_to_string(tag)

    def __getattr__(self, name):
        return getattr(self._raw, name)

    def __repr__(self):
        try:
            name = self._raw.get_name()
        except Exception:
            name = "Anonymous"
        return f"<Adapter({self._raw.__class__.__name__}): {name}>"

    def get_flags(self):
        return getattr(self._raw, "get_flags", lambda: 0)()

    def is_deprecated(self):
        return getattr(self._raw, "is_deprecated", lambda: False)()

    @property
    def callable_type(self):
        if isinstance(self._raw, GIRepository.FunctionInfo):
            return "FunctionInfo"
        elif isinstance(self._raw, GIRepository.SignalInfo):
            return "SignalInfo"
        elif isinstance(self._raw, GIRepository.CallbackInfo):
            return "CallbackInfo"

        raise ValueError(f"Not a valid GI function or callback object or signal. Got: {type(self._raw)}")
