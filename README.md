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


## Getting Started

![flow](.github/assets/flow.png)

You can run Browserq straight on your machine or spin it up with Docker. Check out the [documentation](https://broton.dev/) for all the details, but below is the quick and easy way to jump right in.

Here's what you need to do:
* Get Browserq installed
* Create your own jobs or grab some of [my ready-to-use ones]() (screenshot generation, PDF rendering, etc.)
* Start the server and worker(s) with your jobs
* That's it! Just send requests to queue jobs and grab their results when they're done


### Quick Start

#### Install Browserq

```
pip install browserq
```

#### Define a job

`jobs/screenshot.py`:
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

See `examples/jobs/` for more examples.

#### Run FastAPI server
```
browserq server jobs/
```

Pass job(s) (file or directory) to let the server know which jobs it can accept and how it can validate inputs.

Additionally, `browserq server` accepts arguments that are directly passed to `uvicorn` e.g. `browserq server jobs/ --host 0.0.0.0 --port 42069`.

#### Run Playwright worker(s)
```
browserq worker jobs/
```

Pass the same job(s) as to the server, to let the worker know how to execute them.

#### That's it!

### Using Browserq

Trigger a job execution:
```
curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"name": "pdf", "input": {"url": "https://broton.dev"}}' \
    http://127.0.0.1:8000/jobs
```
