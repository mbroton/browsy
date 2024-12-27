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
    """Collect job class definitions from Python files in the specified path.

    Args:
        path: Path to a Python file or directory containing Python files.
            If a directory is provided, all .py files will be searched recursively.

    Returns:
        A dictionary mapping job names to job classes, where each job class is a subclass
        of BaseJob with a defined NAME class variable.

    Raises:
        ValueError: If the path doesn't exist, no job classes are found, or if there are
            duplicate job names. Also raised if a job class is missing the required NAME
            class variable.
    """
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

        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if not spec or not spec.loader:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

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
        "Found %d job(s) definitions: %s",
        len(jobs),
        ", ".join(sorted(jobs.keys())),
    )

    return jobs


class BaseJob(ABC, BaseModel):
    model_config = ConfigDict(
        frozen=True,
        exclude=["execute"],
        extra="forbid",
    )

    # A unique string identifier for the job type that must be defined by subclasses.
    # This is used to identify and route jobs to the appropriate handler class.
    # For example: NAME = "screenshot" or NAME = "pdf_export"
    NAME: ClassVar[str]

    @abstractmethod
    async def execute(self, page: Page) -> bytes:
        """Execute the job using the provided Playwright page.

        This is the main method that defines the job's behavior. It receives a Playwright's `Page`
        object that can be used to interact with a web browser - navigating to URLs, taking
        screenshots, extracting data, etc.

        This method must be implemented by all job subclasses to define their specific
        automation logic.

        Args:
            page: A Playwright `Page` object representing an automated browser

        Returns:
            bytes: The job's output data in binary format
        """

    async def validate_logic(self) -> bool:
        """Validate job parameters before queueing.

        Since BaseJob inherits from pydantic.BaseModel, basic parameter validation like
        type checking and required fields is handled automatically by Pydantic. This method
        provides additional logical validation that cannot be expressed through Pydantic's
        type system alone.

        For example, if a job accepts either a 'url' or 'html' parameter but not both
        simultaneously, that validation logic should be implemented here since it involves
        checking relationships between multiple fields.

        This method is called before a job is added to the queue. The job will only be
        queued if both Pydantic validation and this logical validation pass.

        Returns:
            bool: True if logical validation passes, False otherwise
        """
        return True
