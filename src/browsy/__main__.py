import asyncio
import logging
import os
import string
import random

import click
import uvicorn

from browsy import DEFAULT_DB_PATH
from browsy.worker import start_worker

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
@click.option(
    "--db-path",
    default=DEFAULT_DB_PATH,
    help="Path to SQLite database file.",
)
@click.argument("uvicorn_args", nargs=-1, type=click.UNPROCESSED)
def server(jobs: str, db_path: str, uvicorn_args: tuple[str]):
    os.environ["BROWSY_JOBS_PATH"] = jobs
    os.environ["BROWSY_DB_PATH"] = db_path
    uvicorn.main(["browsy.server:app"] + list(uvicorn_args))


@cli.command()
@click.argument("jobs", required=True, type=click.Path(exists=True))
@click.option(
    "--db-path",
    type=click.Path(exists=True, dir_okay=False),
    default=DEFAULT_DB_PATH,
    help="Path to SQLite database file.",
)
@click.option(
    "--name", default=None, help="Worker name (random if not provided)"
)
def worker(jobs: str, db_path: str, name: str | None):
    worker_name = name or f"worker_{_get_random_chars(8)}"
    try:
        asyncio.run(
            start_worker(
                name=worker_name,
                db_path=db_path,
                jobs_path=jobs,
            )
        )
    except KeyboardInterrupt:
        logger.info(f"Worker {worker_name} shutting down")


def _get_random_chars(length: int) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


if __name__ == "__main__":
    cli()
