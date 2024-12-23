import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import ClassVar
from pathlib import Path

from playwright.async_api import Page
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


def collect_jobs_defs(path: str | Path) -> dict:
    import importlib.util
    import inspect

    jobs = {}
    path = Path(path) if isinstance(path, str) else path

    if not path.exists():
        raise ValueError(f"Path {path} does not exist")

    logger.info("Selected jobs path: %s", str(path))

    def process_file(file_path: Path) -> None:
        if not file_path.suffix == ".py":
            return

        # Import the module from file path
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if not spec or not spec.loader:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find job classes in the module
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseJob) and obj != BaseJob:
                if not hasattr(obj, "NAME"):
                    raise ValueError(
                        f"Job class {obj.__name__!r} must define a NAME class variable"
                    )
                if obj.NAME in jobs:
                    raise ValueError(
                        f"Duplicated job name {obj.NAME!r}. "
                        "Please ensure all job names are unique."
                    )
                jobs[obj.NAME] = obj

    if path.is_file():
        process_file(path)
    else:
        for file_path in path.rglob("*.py"):
            process_file(file_path)

    if len(jobs) == 0:
        raise ValueError("No job classes found in the specified path")

    logger.info(
        "Found %d job(s): %s", len(jobs), ", ".join(sorted(jobs.keys()))
    )

    return jobs


class BaseJob(ABC, BaseModel):
    model_config = ConfigDict(
        frozen=True,
        exclude=["execute"],
        extra="forbid",
    )

    NAME: ClassVar[str]

    @abstractmethod
    async def execute(self, page: Page) -> bytes:
        """Execute the job using the provided Playwright page."""
