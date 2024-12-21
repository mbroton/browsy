from contextlib import asynccontextmanager
from typing import Annotated
from base64 import b64encode

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app import data, jobs


_JOBS_DEFS: dict[str, type[jobs.BaseJob]]


@asynccontextmanager
async def lifespan(*_):
    global _JOBS_DEFS
    _JOBS_DEFS = jobs.collect_jobs_defs()

    conn = await data.create_connection()

    try:
        await data.init_db(conn)
    finally:
        await conn.close()

    yield


app = FastAPI(lifespan=lifespan)


async def get_db():
    conn = await data.create_connection()

    try:
        yield conn
    finally:
        await conn.close()


class JobRequest(BaseModel):
    name: str
    input: dict


class JobOutput(data.DBOutput):
    output: str

    @field_validator("output", mode="before")
    @classmethod
    def b64encode_output(cls, value: bytes | None) -> str:
        if value is None:
            return ""

        return b64encode(value).decode()


@app.post("/jobs", response_model=data.DBJob)
async def create_job(
    r: JobRequest,
    db_conn: Annotated[data.AsyncConnection, Depends(get_db)],
):
    if r.name not in _JOBS_DEFS:
        raise HTTPException(400, "Job with that name is not defined.")

    input_obj = _JOBS_DEFS[r.name].model_validate(r.input)

    return await data.create_job(db_conn, r.name, input_obj.model_dump_json())


@app.get("/jobs/{job_id}", response_model=data.DBJob)
async def get_job_by_id(
    job_id: int, db_conn: Annotated[data.AsyncConnection, Depends(get_db)]
):
    job = await data.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return job


@app.get("/jobs/{job_id}/result", response_model=JobOutput)
async def get_job_result_by_job_id(
    job_id: int, db_conn: Annotated[data.AsyncConnection, Depends(get_db)]
):
    job = await data.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status == jobs.JobStatus.PENDING:
        raise HTTPException(404, "Job is pending")
    if job.status == jobs.JobStatus.IN_PROGRESS:
        raise HTTPException(404, "Job is in progress")
    if job.status == jobs.JobStatus.FAILED:
        raise HTTPException(500, "Job failed")

    job_result = await data.get_job_result_by_job_id(db_conn, job_id)
    if job_result is None:
        raise HTTPException(500, "Job finished, but there's no result")

    return job_result
