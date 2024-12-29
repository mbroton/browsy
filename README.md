<div align="center">
  <h1>browsy</h1>
</div>

## What is browsy?

browsy is a service that lets you run browser automation tasks without managing browser instances yourself. It provides:

- **Simple Job Definition**: Write Playwright-powered automation tasks in Python
- **HTTP API**: Queue jobs and retrieve results through HTTP endpoints
- **Docker Ready**: Run everything in containers without worrying about browser dependencies
- **Queue System**: Jobs are processed in order, with automatic retries and status tracking
- **Extensible**: Create any browser automation task - from screenshots and PDFs to complex scraping operations

Think of it as a way to turn your Playwright scripts into HTTP services that can be called from anywhere.

## Quick Start

### Download files

You can download required files using a script:
```bash
curl -LsSf https://raw.githubusercontent.com/mbroton/browsy/main/scripts/get.sh | sh
```

The files are: docker-compose file and example jobs.

### Start browsy

```bash
docker compose up --build --scale worker=3
```

Optionally, you can define number of workers. **And that's it!**

Visit `http://localhost:8000/docs` for interactive API documentation (provided by FastAPI).


### Defining jobs

A job is any class that inherits from `browsy.BaseJob`. **browsy** will look for `jobs/` folder and find those classes recursively.

This is an example implementation:
```python
from browsy import BaseJob, Page

# Define a job by inheriting from BaseJob (which works like Pydantic's BaseModel)
# and giving it a unique name
class ScreenshotJob(BaseJob):
    # This name will be used to identify the job type when making API calls
    NAME = "screenshot"

    # Define job parameters
    # All of these will be automatically parsed from the JSON request
    url: str | None = None      # URL to take screenshot of
    html: str | None = None     # Or raw HTML to render
    full_page: bool = False     # Whether to capture the full scrollable page

    async def execute(self, page: Page) -> bytes:
        # This is where the actual browser automation happens
        # `page` is a Playwright `Page` object with all its methods available
        if self.url:
            await page.goto(self.url)
        elif self.html:
            await page.set_content(self.html)
        return await page.screenshot(full_page=self.full_page)

    async def validate_logic(self) -> bool:
        # Optional validation method that runs when submitting a new job
        # Here we check that exactly one of url/html is provided
        if bool(self.url) == bool(self.html):
            return False
        return True
```

Check what you can do with `page` in [Playwright's documentation](https://playwright.dev/python/docs/api/class-page).

Check what you can do with Pydantic's parameters in [Pydantic's documentation](https://docs.pydantic.dev/latest/concepts/models/).


### Client

There's a browsy client to interact with the service. You can install it with:
```bash
pip install browsy
```

and use it like this:

```python
from browsy import BrowsyClient

client = BrowsyClient("http://127.0.0.1")
job_id = client.add_job("screenshot", {
    "url": "https://example.com",
    "full_page": True
})
screenshot = client.get_result(job_id=job_id).content
```

## How it works

![flow](.github/assets/flow.png)

1. You define jobs using Playwright's API
2. Send job requests through HTTP
3. Workers execute jobs in Docker containers
4. Get results when ready

## Documentation

For detailed setup and usage, check out the [documentation](https://broton.dev/).

## License

MIT License - see [LICENSE](LICENSE) for details.
