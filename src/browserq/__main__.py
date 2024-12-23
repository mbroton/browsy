import asyncio
import logging
import os

import click
import uvicorn

from browserq.worker import start_worker, _get_random_chars

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cli")


@click.group()
def cli():
    pass


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("jobs", required=True, type=click.Path(exists=True))
@click.argument("uvicorn_args", nargs=-1, type=click.UNPROCESSED)
def server(jobs: str, uvicorn_args):
    """Run the API server.

    All arguments are passed directly to uvicorn. For example:
    [CLI name] server --host 0.0.0.0 --port 8000 --workers 4
    """
    os.environ["BROWSERQ_JOBS_PATH"] = jobs
    uvicorn.main(["browserq.server:app"] + list(uvicorn_args))


@cli.command()
@click.argument("jobs", required=True, type=click.Path(exists=True))
@click.option(
    "--name", default=None, help="Worker name (random if not provided)"
)
def worker(jobs: str, name: str | None):
    """Run a worker process."""
    worker_name = name or f"worker_{_get_random_chars(8)}"
    try:
        asyncio.run(
            start_worker(
                name=worker_name,
                jobs_path=jobs,
            )
        )
    except KeyboardInterrupt:
        logger.info(f"Worker {worker_name} shutting down")


if __name__ == "__main__":
    cli()
