from typing import TypeAlias
from datetime import datetime
from enum import Enum

import aiosqlite
from pydantic import BaseModel

AsyncConnection: TypeAlias = aiosqlite.Connection

_DB_FILE = "database.sqlite3"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'done', 'in_progress', 'failed')),
    source_type TEXT NOT NULL CHECK (source_type IN ('url', 'html')),
    source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
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


class JobType(str, Enum):
    SCREENSHOT = "screenshot"
    PDF = "pdf"


class JobStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


class JobSourceType(str, Enum):
    URL = "url"
    HTML = "html"


class DBJob(BaseModel):
    """Represents a job record from the database.

    Note: The 'source' field is intentionally excluded from this model."""

    id: int
    type: JobType
    status: JobStatus
    source_type: JobSourceType
    created_at: datetime
    updated_at: datetime | None


class DBOutput(BaseModel):
    id: int
    job_id: int
    output: bytes | None


async def create_connection() -> AsyncConnection:
    conn = await aiosqlite.connect(_DB_FILE)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db(conn: AsyncConnection) -> None:
    await conn.execute("PRAGMA journal_mode = WAL;")
    await conn.commit()

    await conn.executescript(_INIT_SQL)
    await conn.commit()


async def create_job(
    conn: AsyncConnection,
    type_: JobType,
    source_type: JobSourceType,
    source: str,
) -> DBJob:
    async with conn.execute(
        """
        INSERT INTO jobs (type, status, source_type, source)
        VALUES (?, ?, ?, ?)
        RETURNING id, created_at, updated_at
        """,
        (type_, JobStatus.PENDING, source_type, source),
    ) as cursor:
        result = await cursor.fetchone()

    await conn.commit()

    return DBJob(
        type=type_, status=JobStatus.PENDING, source_type=source_type, **result
    )


async def get_job_by_id(
    conn: AsyncConnection,
    id_: int,
) -> DBJob | None:
    async with conn.execute(
        """
        SELECT id, type, status, source_type, created_at, updated_at
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
