from importlib.metadata import version, PackageNotFoundError

from browsy._jobs import BaseJob, Page

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["BaseJob", "Page"]
