<div align="center">
  <h1>:performing_arts: browsy</h1>
</div>

**browsy** is a lightweight queue system for browser automation tasks. It lets you easily schedule and run operations like screenshots, PDF generation, and web scraping through a simple HTTP API - all without external dependencies.


## Getting Started

You can run browsy straight on your machine or spin it up with Docker. Check out the [documentation](https://broton.dev/) for all the details, but below is the quick and easy way to jump right in.

Here's what you need to do:
* Get browsy installed
* Create your own jobs or grab some of [my ready-to-use ones]() (screenshot generation, PDF rendering, etc.)
* Start the server and worker(s) with your jobs
* That's it! Just send requests to queue jobs and grab their results when they're done


### Quick Start

#### Install browsy

```
pip install browsy
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
```

In this example `url`, `html` and `full_page` are fields from Pydantic's `BaseModel`. They are used for new jobs validation.

See `examples/jobs/` for more examples.

#### Run FastAPI server
```
browsy server jobs/
```

Pass job(s) (file or directory) to let the server know which jobs it can accept and how it can validate inputs.

Additionally, `browsy server` accepts arguments that are directly passed to `uvicorn` e.g. `browsy server jobs/ --host 0.0.0.0 --port 42069`.

#### Run Playwright worker(s)
```
browsy worker jobs/
```

Pass the same job(s) as to the server, to let the worker know how to execute them.

#### That's it!

### Using browsy

Trigger a job execution:
```
curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"name": "pdf", "input": {"url": "https://broton.dev"}}' \
    http://127.0.0.1:8000/jobs
```

### Architecture

![flow](.github/assets/flow.png)