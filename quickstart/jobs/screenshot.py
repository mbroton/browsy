from typing import Optional

from browsy import BaseJob, Page


class ScreenshotJob(BaseJob):
    """Generates a screenshot from a webpage or HTML content."""

    NAME = "screenshot"

    url: Optional[str] = None
    html: Optional[str] = None
    full_page: bool = False

    async def execute(self, page: Page) -> bytes:
        if self.url:
            await page.goto(self.url)
        elif self.html:
            await page.set_content(self.html)

        return await page.screenshot(full_page=self.full_page)

    async def validate_logic(self) -> bool:
        return bool(self.url) != bool(self.html)
