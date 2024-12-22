from abc import ABC, abstractmethod
from enum import Enum
from typing import ClassVar

from playwright.async_api import Page
from pydantic import BaseModel, ConfigDict


class JobStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


def collect_jobs_defs():
    import pkgutil
    import importlib
    import inspect
    from pathlib import Path
    from app.jobs import base

    jobs = {}
    package = base.__package__
    package_path = Path(__file__).parent

    for _, name, _ in pkgutil.iter_modules([str(package_path)]):
        module = importlib.import_module(f"{package}.{name}")
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
