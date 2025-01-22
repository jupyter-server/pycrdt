try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version  # type: ignore[import-not-found, no-redef]

__version__ = version("pycrdt")
