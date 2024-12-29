import json
from datetime import datetime
from typing import TypeAlias, Literal

import aiosqlite
from pydantic import BaseModel, field_validator

from browsy import _jobs

AsyncConnection: TypeAlias = aiosqlite.Connection

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    input TEXT NOT NULL CHECK(json_valid(input)),
    status TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at DATETIME,
    worker TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    output BLOB,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);
CREATE INDEX IF NOT EXISTS idx_outputs_job_id ON outputs(job_id);
"""


class DBJob(BaseModel):
    """Represents a job record from the database."""

    id: int
    name: str
    input: dict
    status: _jobs.JobStatus
    created_at: datetime
    updated_at: datetime | None
    worker: str | None

    @field_validator("input", mode="before")
    @classmethod
    def json_str_output(cls, v: str | dict) -> dict:
        if isinstance(v, str):
            return json.loads(v)
        return v


class DBOutput(BaseModel):
    id: int
    job_id: int
    output: bytes | None


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
) -> DBJob:
    async with conn.execute(
        """
        INSERT INTO jobs (name, input, status)
        VALUES (?, ?, ?)
        RETURNING id, created_at, updated_at, worker
        """,
        (name, input_json, _jobs.JobStatus.PENDING),
    ) as cursor:
        result = await cursor.fetchone()

    await conn.commit()

    return DBJob(
        name=name,
        input=input_json,
        status=_jobs.JobStatus.PENDING,
        **result,
    )


async def get_job_by_id(
    conn: AsyncConnection,
    id_: int,
) -> DBJob | None:
    async with conn.execute(
        """
        SELECT id, name, input, status, created_at, updated_at, worker
        FROM jobs
        WHERE id = ?
        """,
        (id_,),
    ) as cursor:
        result = await cursor.fetchone()

    return DBJob(**result) if result else None


async def get_job_result_by_job_id(
    conn: AsyncConnection,
    job_id: int,
) -> DBOutput | None:
    async with conn.execute(
        """
        SELECT id, job_id, output
        FROM outputs
        WHERE job_id = ?
        """,
        (job_id,),
    ) as cursor:
        result = await cursor.fetchone()

    return DBOutput(**result) if result else None


async def get_next_job(conn: AsyncConnection, worker: str) -> DBJob | None:
    # Acquires a reserved lock, blocking other write transactions
    await conn.execute("BEGIN IMMEDIATE")

    async with conn.execute(
        f"""
        SELECT id, name, input, status, created_at, updated_at, worker
        FROM jobs
        WHERE status = '{_jobs.JobStatus.PENDING.value}'
        ORDER BY created_at ASC
        LIMIT 1
        """
    ) as cursor:
        result = await cursor.fetchone()

    if not result:
        # Releases the lock
        await conn.rollback()
        return None

    db_job = DBJob(**result)

    await conn.execute(
        f"""
        UPDATE jobs
        SET status = '{_jobs.JobStatus.IN_PROGRESS.value}', updated_at = DATETIME('now'), worker = ?
        WHERE id = ?
        """,
        (worker, db_job.id),
    )
    await conn.commit()
    db_job.status = _jobs.JobStatus.IN_PROGRESS
    db_job.worker = worker

    return db_job


async def update_job_status(
    conn: AsyncConnection,
    job_id: int,
    status: Literal[_jobs.JobStatus.DONE, _jobs.JobStatus.FAILED],
    output: bytes | None,
) -> None:
    await conn.execute(
        """
        UPDATE jobs
        SET status = ?, updated_at = DATETIME('now')
        WHERE id = ?
        """,
        (status, job_id),
    )

    if output:
        await conn.execute(
            """
            INSERT INTO outputs (job_id, output)
            VALUES (?, ?)
            """,
            (job_id, output),
        )

    await conn.commit()
