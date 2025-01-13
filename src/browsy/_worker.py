import asyncio
import logging
import signal
import time
from typing import Optional

from playwright.async_api import (
    PlaywrightContextManager,
    Browser,
    Error as PlaywrightError,
)
from playwright._impl._errors import TargetClosedError

from browsy import _database, _jobs, _models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("worker")

_JOB_POLL_INTERVAL = 5
_HEARTBEAT_LOG_INTERVAL = 60


async def _worker_loop(name: str, db_path: str, jobs_path: str) -> None:
    worker_logger = logging.getLogger(name)

    db = await _database.create_connection(db_path)
    jobs_defs = _jobs.collect_jobs_defs(jobs_path)
    await _database.check_in_worker(db, name)

    pw = await PlaywrightContextManager().start()
    browser: Browser = await pw.chromium.launch(headless=True)
    worker_logger.info("Browser launched and ready")

    worker_heartbeat = time.monotonic()
    job: Optional[_database.DBJob] = None
    start_time: Optional[float] = None

    try:
        while True:
            job = await _database.get_next_job(db, name)
            if not job:
                if (
                    time.monotonic() - worker_heartbeat
                    >= _HEARTBEAT_LOG_INTERVAL
                ):
                    await _database.update_worker_activity(db, name)
                    worker_heartbeat = time.monotonic()
                worker_logger.debug(
                    f"No jobs available, sleeping for {_JOB_POLL_INTERVAL}s"
                )
                await asyncio.sleep(_JOB_POLL_INTERVAL)
                continue

            worker_logger.info(f"Starting job {job.id} (type: {job.name})")

            start_time = time.monotonic()
            worker_heartbeat = time.monotonic()
            ctx = await browser.new_context()
            page = await ctx.new_page()

            try:
                output = await asyncio.create_task(
                    jobs_defs[job.name](**job.input).execute(page)
                )
                worker_logger.info(f"Job {job.id} completed successfully")
                await _database.update_job_status(
                    db,
                    worker=name,
                    job_id=job.id,
                    status=_models.JobStatus.DONE,
                    processing_time=_calc_processing_time(start_time),
                    output=output,
                )
                job = None
                start_time = None

            except PlaywrightError:
                # We only catch PlaywrightError since they are somewhat expected
                # (e.g. network issues, invalid URLs). Other exceptions like
                # bugs in job implementation should crash the worker to surface
                # the issue.
                worker_logger.exception(
                    f"Playwright error occurred for job {job.id}."
                    " Marking job as failed."
                )
                await _database.update_job_status(
                    db,
                    worker=name,
                    job_id=job.id,
                    status=_models.JobStatus.FAILED,
                    processing_time=_calc_processing_time(start_time),
                    output=None,
                )
                job = None
                start_time = None

            finally:
                await page.close()
                await ctx.close()

    except BaseException as e:
        if job:
            worker_logger.info(
                f"Job {job.id} was in progress, marking as failed"
            )
            await _database.update_job_status(
                db,
                worker=name,
                job_id=job.id,
                status=_jobs.JobStatus.FAILED,
                processing_time=(
                    _calc_processing_time(start_time) if start_time else 0
                ),
                output=None,
            )

        # Don't propagate CancelledError since it's expected during shutdown
        if not isinstance(e, asyncio.CancelledError):
            raise

    finally:
        await pw.stop()
        await db.close()


def _calc_processing_time(s: float) -> int:
    # Calculate job processing time in milliseconds
    return round((time.monotonic() - s) * 1000)


def _shutdown(main_task: asyncio.Task, s: signal.Signals) -> None:
    logger.info(f"Received shutdown signal {s.name!r}. Shutting down...")
    main_task.cancel()


def start_worker(name: str, db_path: str, jobs_path: str) -> None:
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(_worker_loop(name, db_path, jobs_path))

    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, lambda sig=s: _shutdown(main_task, sig))

    try:
        loop.run_until_complete(main_task)
    except Exception as e:
        # TargetClosedError is expected when stopping worker during job execution
        # since it's caused by browser context being closed. Other Playwright errors
        # that occur during normal job execution are caught in the worker loop.
        if not isinstance(e, TargetClosedError):
            logger.error(
                "Worker process is shutting down due to unexpected error"
            )
            raise
    finally:
        loop.close()
