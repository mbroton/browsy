<div align="center">
  <h1>:performing_arts: browserq</h1>
</div>

**browserq** is a simple starter kit for executing browser automation tasks via HTTP requests. It uses Playwright for browser interactions and a lightweight SQLite-based queue for task management, making it easy to get started without requiring external databases or message brokers.

## Why browserq?

* **🔌 Simple HTTP API:** Clean API for submitting tasks, checking status, and retrieving results. Perfect for integration into existing workflows.

* **🌐 Browser Automation Ready:** Execute tasks like screenshot generation, PDF rendering, HTML previews or web scraping with Playwright. Supports both URL and raw HTML inputs.

* **🛠 Self-Contained:** No need for PostgreSQL, Redis, or message queues—just a lightweight, independent service that runs locally or in a container.

* **📋 Persistent Queue:** SQLite ensures tasks persist even if the server or workers restart, providing ACID compliance without external dependencies.

* **🏗️ Production Features:** Includes graceful shutdown, comprehensive error handling, automatic browser cleanup, and structured logging out of the box.


## Use Cases

* **Screenshot generation:** send a URL or raw HTML to the service and get a screenshot of the rendered page **(included in the template)**.

* **PDF Rendering:** submit a URL or HTML payload to generate and download a PDF of the page **(included in the template)**.

* **Basic Web Scraping:** extract data from a webpage, such as text or metadata.

* **Static HTML Previews:** convert raw HTML input into rendered page previews for QA or content review.


## Getting Started

### Install
```
pip install browserq
```

### Define example job (see `examples/jobs/`)
```py
from browserq import BaseJob, Page

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
```

In this example `url`, `html` and `full_page` are fields from Pydantic's `BaseModel`. They are used for new jobs validation.

### Run the server
```
browserq server [file job or directory] [uvicorn params]
```

for example:
```
browserq server jobs/screenshot.py --host 0.0.0.0 --port 8000
```

### Run worker(s)
```
browserq worker [file job or directory]
```
