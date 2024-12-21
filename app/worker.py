import asyncio
import logging
import time

from playwright.async_api import async_playwright, PlaywrightContextManager
import playwright._impl._errors
import playwright.async_api

from app import data, jobs

_JOB_POLL_INTERVAL = 5
_HEARTBEAT_LOG_INTERVAL = 600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("master")


async def worker_loop(
    p: PlaywrightContextManager,
    conn: data.AsyncConnection,
    logger: logging.Logger,
) -> None:
    logger.info("Starting")
    shutdown = False
    last_heartbeat = time.monotonic()
    browser = None
    current_job_task = None

    try:
        browser = await p.chromium.launch(headless=True)

        while not shutdown:
            timeref = time.monotonic()

            try:
                job = await data.get_next_job(conn)
                if not job:
                    if timeref - last_heartbeat >= _HEARTBEAT_LOG_INTERVAL:
                        logger.info("Worker is alive and polling for jobs")
                        last_heartbeat = timeref

                    await asyncio.sleep(_JOB_POLL_INTERVAL)
                    continue

                last_heartbeat = timeref
                logger.info(f"Starting job {job.type!r} (ID: {job.id})")

                try:
                    async with await browser.new_context() as ctx:
                        async with await ctx.new_page() as page:
                            current_job_task = asyncio.create_task(
                                jobs.JOB_TYPE_TO_FUNC[job.type](
                                    page, job.source_type, job.source
                                )
                            )
                            output = await current_job_task

                except (asyncio.CancelledError, playwright.async_api.Error):
                    logger.error(
                        f"Job interrupted, marking {job.id} as failed."
                    )
                    if current_job_task and not current_job_task.done():
                        current_job_task.cancel()
                        try:
                            await current_job_task
                        except Exception as e:
                            logger.debug(f"Task cleanup error: {e!r}")
                    job.status = jobs.JobStatus.FAILED
                    await data.finish_job(conn, job.id, job.status, None)
                    shutdown = True
                    break

                except Exception:
                    logger.exception("Job execution failed.")
                    job.status = jobs.JobStatus.FAILED

                else:
                    logger.info(f"Job {job.id} is done.")
                    job.status = jobs.JobStatus.DONE

                await data.finish_job(
                    conn,
                    job.id,
                    job.status,
                    (output if job.status == jobs.JobStatus.DONE else None),
                )

            except asyncio.CancelledError:
                logger.info("Shutting down worker (no jobs interrupted).")
                shutdown = True
                break

    finally:
        if current_job_task and not current_job_task.done():
            current_job_task.cancel()
            try:
                await current_job_task
            except Exception as e:
                logger.debug(f"Task cleanup error: {e!r}")

        if browser:
            try:
                await asyncio.wait_for(browser.close(), timeout=5.0)
            except (asyncio.TimeoutError, playwright.async_api.Error) as e:
                logger.warning(f"Failed to close browser gracefully: {e!r}")


async def start_worker(name: str) -> None:
    lg = logging.getLogger(name)
    conn = await data.create_connection()
    try:
        async with async_playwright() as p:
            await worker_loop(p, conn, lg)
    finally:
        await conn.close()


async def main() -> None:
    await start_worker("worker1")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
