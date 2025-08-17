# src/ca_proto/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"  # bump when you tag; used as a fallback/display

def get_version() -> str:
    """
    Return the installed package version if available, else fallback to __version__.
    """
    try:
        from importlib.metadata import version as _v
        return _v("ca-proto")
    except Exception:
        return __version__

