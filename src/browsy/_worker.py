import asyncio
import logging
import time
import os
from pathlib import Path

from playwright.async_api import (
    async_playwright,
    PlaywrightContextManager,
    Browser,
)
import playwright._impl._errors
import playwright.async_api

from browsy import _database, _jobs

_JOB_POLL_INTERVAL = 5
_HEARTBEAT_LOG_INTERVAL = 600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("worker-main")


async def worker_loop(
    pw_ctx: PlaywrightContextManager,
    db: _database.AsyncConnection,
    name: str,
    jobs_defs: dict[str, type[_jobs.BaseJob]],
) -> None:
    log = logging.getLogger(name)
    log.info("Ready to work")
    shutdown = False
    last_heartbeat = time.monotonic()
    browser: Browser | None = None
    current_job_task: asyncio.Task | None = None

    try:
        browser = await pw_ctx.chromium.launch(headless=True)

        while not shutdown:
            timeref = time.monotonic()

            try:
                job = await _database.get_next_job(db, worker=name)
                if not job:
                    if timeref - last_heartbeat >= _HEARTBEAT_LOG_INTERVAL:
                        log.info("Worker is alive and polling for jobs")
                        last_heartbeat = timeref

                    await asyncio.sleep(_JOB_POLL_INTERVAL)
                    continue

                last_heartbeat = timeref
                log.info(f"Starting job {job.id} ({job.name!r})")

                try:
                    async with await browser.new_context() as ctx:
                        async with await ctx.new_page() as page:
                            current_job_task = asyncio.create_task(
                                jobs_defs[job.name](**job.input).execute(page)
                            )
                            output = await current_job_task

                except (asyncio.CancelledError, playwright.async_api.Error):
                    log.error(f"Job interrupted, marking {job.id} as failed")
                    await _cancel_task(current_job_task)
                    job.status = _jobs.JobStatus.FAILED
                    await _database.update_job_status(
                        db, job.id, job.status, None
                    )
                    shutdown = True
                    break

                except Exception:
                    log.exception("Job execution failed")
                    job.status = _jobs.JobStatus.FAILED

                else:
                    log.info(f"Job {job.id} is done")
                    job.status = _jobs.JobStatus.DONE

                output = output if job.status == _jobs.JobStatus.DONE else None
                await _database.update_job_status(
                    db, job.id, job.status, output
                )

            except asyncio.CancelledError:
                log.info("Shutting down worker (no jobs interrupted)")
                shutdown = True
                break

    finally:
        await _cancel_task(current_job_task, log=log)

        if browser:
            await _shutdown_browser(browser, log=log)


async def _cancel_task(
    task: asyncio.Task | None, log: logging.Logger | None = None
) -> None:
    log = log or logger
    if task and not task.done():
        task.cancel()
        try:
            await task
        except Exception as e:
            log.debug(f"Canceled task clean up error: {e!r}")


async def _shutdown_browser(
    browser: Browser, timeout: float = 5.0, log: logging.Logger | None = None
) -> None:
    log = log or logger
    try:
        await asyncio.wait_for(browser.close(), timeout=timeout)
    except (asyncio.TimeoutError, playwright.async_api.Error) as e:
        log.warning(f"Failed to close browser gracefully: {e!r}")


async def start_worker(
    name: str, db_path: str, jobs_path: str | None = None
) -> None:
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    jobs_path = jobs_path or Path().absolute()
    jobs_defs = _jobs.collect_jobs_defs(jobs_path)
    conn = await _database.create_connection(db_path)

    try:
        async with async_playwright() as p:
            await worker_loop(pw_ctx=p, db=conn, name=name, jobs_defs=jobs_defs)
    finally:
        await conn.close()
