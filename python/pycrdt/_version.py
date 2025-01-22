try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:  # pragma: no cover
    from importlib_metadata import (  # type: ignore[assignment, import-not-found, no-redef]
        PackageNotFoundError,
        version,
    )

try:
    __version__ = version("pycrdt")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "uninstalled"
