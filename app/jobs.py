from enum import Enum
from typing import Callable, Awaitable, TypeAlias

from playwright.async_api import Page


class JobStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


class JobSourceType(str, Enum):
    URL = "url"
    HTML = "html"


async def _set_page_state(
    page: Page, source_type: JobSourceType, source: str
) -> None:
    if source_type == JobSourceType.URL:
        await page.goto(source)
    elif source_type == JobSourceType.HTML:
        await page.set_content(source)
    else:
        raise ValueError(source_type)


# Jobs must comply with this type to be usable in the worker.
_JobFuncType: TypeAlias = Callable[[Page, JobSourceType, str], Awaitable[bytes]]


async def get_screenshot_job(
    page: Page, source_type: JobSourceType, source: str
) -> bytes:
    await _set_page_state(page, source_type, source)
    return await page.screenshot()


async def get_pdf_job(
    page: Page, source_type: JobSourceType, source: str
) -> bytes:
    await _set_page_state(page, source_type, source)
    return await page.pdf()


# After implementing a new job function, it must be added
# to `JobType` (this way it can be passed in the API request),
# and to `JOB_TYPE_TO_FUNC` mapping to be available for use in the worker.


class JobType(str, Enum):
    SCREENSHOT = "screenshot"
    PDF = "pdf"


JOB_TYPE_TO_FUNC: dict[JobType, _JobFuncType] = {
    JobType.SCREENSHOT: get_screenshot_job,  # type: ignore
    JobType.PDF: get_pdf_job,  # type: ignore
}
