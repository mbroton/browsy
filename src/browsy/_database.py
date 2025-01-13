from datetime import datetime
from typing import Literal, Optional, List, Tuple

import aiosqlite
from pydantic import BaseModel

from browsy import _models

AsyncConnection = aiosqlite.Connection

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    input TEXT NOT NULL CHECK(json_valid(input)),
    status TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at DATETIME,
    worker TEXT,
    processing_time INTEGER
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    last_check_in_time DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    last_activity_time DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_workers_name ON workers(name);

CREATE TABLE IF NOT EXISTS outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    output BLOB,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);
CREATE INDEX IF NOT EXISTS idx_outputs_job_id ON outputs(job_id);
"""


class DBOutput(BaseModel):
    id: int
    job_id: int
    output: Optional[bytes]


class DBWorker(BaseModel):
    id: int
    name: str
    last_check_in_time: datetime
    last_activity_time: datetime

    @property
    def uptime(self) -> datetime:
        return datetime.now()


async def create_connection(db_path: str) -> AsyncConnection:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db(conn: AsyncConnection) -> None:
    await conn.execute("PRAGMA journal_mode = WAL;")
    await conn.commit()

    await conn.executescript(_INIT_SQL)
    await conn.commit()


async def create_job(
    conn: AsyncConnection,
    name: str,
    input_json: str,
) -> _models.Job:
    async with conn.execute(
        """
        INSERT INTO jobs (name, input, status)
        VALUES (?, ?, ?)
        RETURNING id, created_at, updated_at, worker, processing_time
        """,
        (name, input_json, _models.JobStatus.PENDING),
    ) as cursor:
        result = await cursor.fetchone()

    await conn.commit()

    return _models.Job(
        name=name,
        input=input_json,
        status=_models.JobStatus.PENDING,
        **result,
    )


async def get_job_by_id(
    conn: AsyncConnection,
    id_: int,
) -> Optional[_models.Job]:
    async with conn.execute(
        """
        SELECT id, name, input, status, created_at, updated_at, worker, processing_time
        FROM jobs
        WHERE id = ?
        """,
        (id_,),
    ) as cursor:
        result = await cursor.fetchone()

    return _models.Job(**result) if result else None


async def get_job_result_by_job_id(
    conn: AsyncConnection,
    job_id: int,
) -> Optional[bytes]:
    async with conn.execute(
        """
        SELECT id, job_id, output
        FROM outputs
        WHERE job_id = ?
        """,
        (job_id,),
    ) as cursor:
        result = await cursor.fetchone()

    return result["output"] if result else None


async def get_next_job(
    conn: AsyncConnection, worker: str
) -> Optional[_models.Job]:
    # Acquires a reserved lock, blocking other write transactions
    await conn.execute("BEGIN IMMEDIATE")

    async with conn.execute(
        f"""
        SELECT id, name, input, status, created_at, updated_at, worker, processing_time
        FROM jobs
        WHERE status = '{_models.JobStatus.PENDING.value}'
        ORDER BY created_at ASC
        LIMIT 1
        """
    ) as cursor:
        result = await cursor.fetchone()

    if not result:
        # Releases the lock
        await conn.rollback()
        return None

    db_job = _models.Job(**result)

    await conn.execute(
        f"""
        UPDATE jobs
        SET status = '{_models.JobStatus.IN_PROGRESS.value}', updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now'), worker = ?
        WHERE id = ?
        """,
        (worker, db_job.id),
    )

    await update_worker_activity(conn, worker, commit=False)

    await conn.commit()
    db_job.status = _models.JobStatus.IN_PROGRESS
    db_job.worker = worker

    return db_job


async def update_job_status(
    conn: AsyncConnection,
    worker: str,
    job_id: int,
    status: Literal[_models.JobStatus.DONE, _models.JobStatus.FAILED],
    processing_time: int,
    output: Optional[bytes],
) -> None:
    await conn.execute(
        """
        UPDATE jobs
        SET status = ?, updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now'), processing_time = ?
        WHERE id = ?
        """,
        (status, processing_time, job_id),
    )

    if output:
        await conn.execute(
            """
            INSERT INTO outputs (job_id, output)
            VALUES (?, ?)
            """,
            (job_id, output),
        )

    await update_worker_activity(conn, worker, commit=False)

    await conn.commit()


async def check_in_worker(
    conn: AsyncConnection,
    worker: str,
) -> None:
    """Updates worker's last check-in timestamp."""
    await conn.execute(
        """
        INSERT INTO workers (name, last_check_in_time)
        VALUES (?, strftime('%Y-%m-%d %H:%M:%f', 'now'))
        ON CONFLICT(name) DO UPDATE SET
            last_check_in_time = strftime('%Y-%m-%d %H:%M:%f', 'now')
        """,
        (worker,),
    )
    await conn.commit()


async def update_worker_activity(
    conn: AsyncConnection, worker: str, commit: bool = True
) -> None:
    """Updates worker's last activity timestamp."""
    await conn.execute(
        """
        UPDATE workers
        SET last_activity_time = strftime('%Y-%m-%d %H:%M:%f', 'now')
        WHERE name = ?
        """,
        (worker,),
    )
    if commit:
        await conn.commit()


async def get_workers(
    conn: AsyncConnection, last_activity_time_ge: Optional[datetime] = None
) -> List[DBWorker]:
    args = []
    query = """SELECT id, name, last_check_in_time, last_activity_time
                    FROM workers"""
    if last_activity_time_ge:
        query += " WHERE last_activity_time >= ?"
        args.append(last_activity_time_ge)

    query += " ORDER BY last_activity_time DESC"

    async with conn.execute(query, args) as cursor:
        result = await cursor.fetchall()

    if not result:
        return []

    return [DBWorker(**r) for r in result]


async def get_jobs(
    conn: AsyncConnection,
    status: Optional[_models.JobStatus] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Tuple[List[_models.JobBase], int]:
    limit = limit or 50
    offset = offset or 0

    args = []
    where_clause = ""
    if status:
        where_clause = " WHERE status = ? "
        args.append(status)

    count_query = f"SELECT COUNT(*) FROM jobs{where_clause}"
    async with conn.execute(count_query, args) as cursor:
        total_count = (await cursor.fetchone())[0]

    query = f"""
        SELECT id, name, status, created_at, updated_at, worker, processing_time
        FROM jobs{where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    args.extend([limit, offset])

    async with conn.execute(query, args) as cursor:
        rows = await cursor.fetchall()

    jobs = [_models.JobBase(**r) for r in rows]

    return jobs, total_count
