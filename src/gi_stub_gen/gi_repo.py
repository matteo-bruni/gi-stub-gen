import gi
import logging
from typing import Self, Type, TypeVar, overload

logger = logging.getLogger(__name__)

try:
    gi.require_version("GioUnix", "2.0")
    gi.require_version("GIRepository", "3.0")
except ValueError:
    raise RuntimeError("GIRepository 3.0 is required")

from gi.repository import GIRepository  # noqa: E402

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

        # Simple cache key to avoid repeated C calls
        key = f"{namespace}-{version}"
        if key in self._loaded_namespaces:
            return

        gi_to_import = namespace.removeprefix("gi.repository.")
        if version is not None:
            try:
                self._repo.require(
                    gi_to_import,
                    version,
                    GIRepository.RepositoryLoadFlags.NONE,
                )
                self._loaded_namespaces.add(key)
            except Exception as e:
                logger.error(
                    f"Impossible to load {gi_to_import} {version=}: {e}",
                )

    @overload
    def find_by_name(
        self,
        namespace: str,
        name: str,
        namespace_version: str | None = None,
        target_type: Type[T] = ...,
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
        target_type: Type[GIRepository.BaseInfo] | None = None,
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
            raise TypeError(
                f"Expected {namespace}.{name} to be {target_type.__name__}, "
                f"got {type(info).__name__}"
            )

        return info
