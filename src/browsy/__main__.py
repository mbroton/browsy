import asyncio
import logging
import os
import string
import random

import click

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cli")


@click.group()
def cli():
    pass


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("uvicorn_args", nargs=-1, type=click.UNPROCESSED)
def server(uvicorn_args: tuple[str]):
    _validate_env_vars()

    import uvicorn

    uvicorn.main(["browsy._server:app"] + list(uvicorn_args))


@cli.command()
@click.option(
    "--name", default=None, help="Worker name (random if not provided)"
)
def worker(name: str | None):
    _validate_env_vars()

    from browsy._worker import start_worker

    worker_name = name or f"worker_{_get_random_chars(8)}"
    try:
        asyncio.run(
            start_worker(
                name=worker_name,
                db_path=os.environ["BROWSY_DB_PATH"],
                jobs_path=os.environ["BROWSY_JOBS_PATH"],
            )
        )
    except KeyboardInterrupt:
        logger.info(f"Worker {worker_name} shutting down")


def _get_random_chars(length: int) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _validate_env_vars() -> None:
    jobs_path = os.environ.get("BROWSY_JOBS_PATH")
    db_path = os.environ.get("BROWSY_DB_PATH")

    if not jobs_path and not db_path:
        raise ValueError(
            "BROWSY_JOBS_PATH and BROWSY_DB_PATH"
            " environment variables are required"
        )


if __name__ == "__main__":
    cli()
