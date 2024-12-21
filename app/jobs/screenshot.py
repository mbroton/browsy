from playwright.async_api import Page

from app.jobs import BaseJob


class ScreenshotJob(BaseJob):
    NAME = "screenshot"

    url: str | None = None
    html: str | None = None
    full_size: bool = False

    async def execute(self, page: Page) -> bytes:
        if self._data.url:
            await page.goto(self._data.url)
        elif self._data.html:
            await page.set_content(self._data.html)

        return await page.screenshot(full_page=self._data.full_size)
