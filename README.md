<div align="center">
  <h1>:performing_arts: browsy</h1>
</div>

**browsy** is a lightweight queue system for browser automation tasks. It lets you easily schedule and run operations like screenshots, PDF generation, and web scraping through a simple HTTP API - all without external dependencies.


## Getting Started

The simplest way to spin browsy up is with Docker Compose. Check out the [documentation](https://broton.dev/) for all the details, but below is the quick and easy way to jump right in.

Here's what you need to do:
* Install browsy
* Copy docker-compose.yml
* Define jobs
* Run docker compose
* That's it! Just send requests to queue jobs and grab their results when they're done


### Quick Start

#### Install browsy

```
pip install browsy
```

#### Copy docker compose

```
git clone ...
```

#### Define a job

`jobs/screenshot.py`:
```py
from browsy import BaseJob, Page

class ScreenshotJob(BaseJob):
    NAME = "screenshot"

    url: str | None = None
    html: str | None = None
    full_page: bool = False

    async def execute(self, page: Page) -> bytes:
        if self.url:
            await page.goto(self.url)
        elif self.html:
            await page.set_content(self.html)

        return await page.screenshot(full_page=self.full_page)

    async def validate_logic(self) -> bool:
        # Ensure only one target is given, never both
        if bool(self.url) == bool(self.html):
            return False
        
        return True
```

In this example `url`, `html` and `full_page` are fields from Pydantic's `BaseModel`. They are used for new jobs validation.

#### Run browsy

```
docker compose up --build
```

#### That's it!

### Using browsy

Trigger a job execution:
```py
from browsy import BrowsyClient

client = BrowsyClient("http://127.0.0.1")
job_id = client.add_job("screenshot", {"url": "https://broton.dev", full_page=True})
screenshot = client.get_result(job_id=job_id).content
```

### Architecture

![flow](.github/assets/flow.png)