from typing import Literal, Optional, Union

from browsy import BaseJob, Page


class PDFJob(BaseJob):
    """Generates a PDF from a webpage or HTML content."""

    NAME = "pdf"

    url: Optional[str] = None
    html: Optional[str] = None
    emulate_media: Union[Literal["null", "print", "screen"], None] = None

    async def execute(self, page: Page) -> bytes:
        if self.url:
            await page.goto(self.url)
        elif self.html:
            await page.set_content(self.html)

        if self.emulate_media:
            await page.emulate_media(self.emulate_media)

        return await page.pdf()

    async def validate_logic(self) -> bool:
        return bool(self.url) != bool(self.html)
