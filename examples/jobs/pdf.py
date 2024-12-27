from typing import Literal

from browsy import BaseJob, Page


class PDFJob(BaseJob):
    NAME = "pdf"

    url: str | None = None
    html: str | None = None
    emulate_media: Literal["null", "print", "screen"] | None = None

    async def execute(self, page: Page) -> bytes:
        if self.url:
            await page.goto(self.url)
        elif self.html:
            await page.set_content(self.html)

        if self.emulate_media:
            await page.emulate_media(self.emulate_media)

        return await page.pdf()
