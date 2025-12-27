from __future__ import annotations
import gi
import logging
from typing import TypeVar, overload
from typing_extensions import Self

try:
    gi.require_version("GioUnix", "2.0")
    gi.require_version("GIRepository", "3.0")
except ValueError:
    raise RuntimeError("GIRepository 3.0 is required")

from gi.repository import GIRepository  # noqa: E402
from gi_stub_gen.adapter import GIRepositoryCallableAdapter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=GIRepository.BaseInfo)


class GIRepo:
    """
    Manages the GI Repository 3.0 access as a singleton.
    """

    _instance = None
    _repo: GIRepository.Repository | None = None
    _loaded_namespaces: set[str] = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GIRepo, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._repo = GIRepository.Repository.new()
        self._loaded_namespaces = set()

    @classmethod
    def get(cls) -> Self:
        return cls()

    @classmethod
    def reset(cls):
        """
        Resets the singleton state.
        """
        if cls._instance:
            cls._instance._initialize()

    @property
    def raw(self) -> GIRepository.Repository:
        """Get the raw GIRepository.Repository instance."""
        if self._repo is None:
            raise RuntimeError("GIRepo not initialized")
        return self._repo

    def require(
        self,
        namespace: str,
        version: str | None = None,
    ) -> None:
        """
        Load a namespace into the repository.
        """
        assert self._repo is not None, "GIRepo not initialized"

        namespace = namespace.removeprefix("gi.repository.")

        # Simple cache key to avoid repeated C calls
        key = f"{namespace}-{version}" if version is not None else namespace
        if key in self._loaded_namespaces:
            return

        if version is not None:
            try:
                self._repo.require(
                    namespace,
                    version,
                    GIRepository.RepositoryLoadFlags.NONE,
                )
                self._loaded_namespaces.add(key)
            except Exception as e:
                logger.error(
                    f"Impossible to load {namespace} {version=}: {e}",
                )

    @overload
    def find_by_name(
        self,
        namespace: str,
        name: str,
        namespace_version: str | None = None,
        target_type: type[T] = ...,
    ) -> T | None: ...

    @overload
    def find_by_name(
        self,
        namespace: str,
        name: str,
        namespace_version: str | None = None,
    ) -> GIRepository.BaseInfo | None: ...

    def find_by_name(
        self,
        namespace: str,
        name: str,
        namespace_version: str | None = None,
        target_type: type[GIRepository.BaseInfo] | None = None,
    ) -> GIRepository.BaseInfo | None:
        """
        Find a GIRepository info object by its namespace and name.
        If the namespace is not loaded, tries to load it first.
        Returns None if not found.

        e.g. find_by_name("Gst", "AllocationParams")
        """

        try:
            self.require(namespace, namespace_version)
        except RuntimeError:
            # if it fails, just ignore
            pass

        assert self._repo is not None, "GIRepo not initialized"
        info = self._repo.find_by_name(namespace, name)

        if info is None:
            return None

        if target_type is not None and not isinstance(info, target_type):
            raise TypeError(f"Expected {namespace}.{name} to be {target_type.__name__}, got {type(info).__name__}")

        return info

    def find_callable(
        self,
        namespace: str,
        name: str,
        namespace_version: str | None = None,
    ) -> GIRepositoryCallableAdapter | None:
        """
        Find a callable GIRepository info object by its namespace and name.
        If the namespace is not loaded, tries to load it first.
        Returns None if not found.

        The returned object is wrapped in a GIRepositoryCallableAdapter for compatibility
        with pygobject overrides.
        """

        info = self.find_by_name(
            namespace,
            name,
            namespace_version,
        )

        if info is None:
            return None

        is_callable = isinstance(info, GIRepository.CallableInfo)
        if not is_callable:
            raise TypeError(f"Expected {namespace}.{name} to be CallableInfo, got {type(info).__name__}")

        return GIRepositoryCallableAdapter(info)


if __name__ == "__main__":
    # ti_info = repo.find_by_name(
    #     "GLib",
    #     "IO_FLAG_APPEND",
    #     namespace_version="2.0",
    #     # target_type=GIRepository.ObjectInfo,
    # )

    # assert ti_info is not None
    # for i in range(ti_info.get_n_signals()):
    #     signal_info = ti_info.get_signal(i)
    #     print("Signal:", signal_info.get_name())

    # for i in range(ti_info.get_n_fields()):
    #     field_info = ti_info.get_field(i)
    #     print("Field:", field_info.get_name())

    # for i in range(ti_info.get_n_methods()):
    #     method_info = ti_info.get_method(i)
    #     print("Method:", method_info.get_name())

    # for i in range(ti_info.get_n_vfuncs()):
    #     vfunc_info = ti_info.get_vfunc(i)
    #     print("VFunc:", vfunc_info.get_name())

    # for i in range(ti_info.get_n_interfaces()):
    #     interface_info = ti_info.get_interface(i)
    #     print("Interface:", interface_info.get_name())

    # for i in range(ti_info.get_n_properties()):
    #     property_info = ti_info.get_property(i)
    #     print("Property:", property_info.get_name())

    repo = GIRepo()
    pygobject_adapter = repo.find_callable(
        "GObject",
        "ClosureMarshal",
        namespace_version="2.0",
    )
    if pygobject_adapter is None:
        raise RuntimeError("Could not find ClosureMarshal")

    from gi_stub_gen.schema.function import FunctionSchema, CallbackSchema

    c = CallbackSchema(
        function=FunctionSchema.from_gi_object(
            obj=pygobject_adapter,
            docstring=None,
        ),
        originated_from={"Manual from GIRepository"},
        name="ClosureMarshal",
    )
    breakpoint()
