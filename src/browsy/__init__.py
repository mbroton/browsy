from importlib.metadata import version, PackageNotFoundError

from browsy._jobs import BaseJob, Page
from browsy._models import JobBase, Job, JobStatus
from browsy._client import BrowsyClient, AsyncBrowsyClient

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "BaseJob",
    "Page",
    "JobBase",
    "Job",
    "JobStatus",
    "BrowsyClient",
    "AsyncBrowsyClient",
]
