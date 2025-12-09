from typing import Self
import gi


try:
    gi.require_version("GIRepository", "3.0")
except ValueError:
    raise RuntimeError("GIRepository 3.0 is required")

from gi.repository import GIRepository


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
        NOTE: Crucial in 3.0 because the repo starts empty.
        """
        assert self._repo is not None, "GIRepo not initialized"

        # Simple cache key to avoid repeated C calls
        key = f"{namespace}-{version}"
        if key in self._loaded_namespaces:
            return

        try:
            self._repo.require(
                namespace,
                version,
                GIRepository.RepositoryLoadFlags.NONE,
            )
            self._loaded_namespaces.add(key)
        except Exception as e:
            raise RuntimeError(
                f"Impossible to load {namespace} v{version}: {e}",
            )

    def find_by_name(
        self,
        namespace: str,
        name: str,
        namespace_version: str | None = None,
    ) -> GIRepository.BaseInfo | None:
        """
        Find a GIRepository info object by its namespace and name.
        If the namespace is not loaded, tries to load it first.
        Returns None if not found.
        """

        try:
            self.require(namespace, namespace_version)
        except RuntimeError:
            # if it fails, just ignore
            pass

        return self.raw.find_by_name(namespace, name)
