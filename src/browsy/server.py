import os
from contextlib import asynccontextmanager
from typing import Annotated
from base64 import b64encode
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from browsy import jobs, database, DEFAULT_DB_PATH


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("BROWSY_DB_PATH", DEFAULT_DB_PATH)
    jobs_path = os.environ.get("BROWSY_JOBS_PATH", str(Path().absolute()))

    app.state.DB_PATH = db_path
    app.state.JOBS_DEFS = jobs.collect_jobs_defs(jobs_path)

    conn = await database.create_connection(db_path)

    try:
        await database.init_db(conn)
    finally:
        await conn.close()

    yield


app = FastAPI(lifespan=lifespan)


async def get_db(request: Request):
    conn = await database.create_connection(request.app.state.DB_PATH)

    try:
        yield conn
    finally:
        await conn.close()


class JobRequest(BaseModel):
    name: str
    input: dict


class JobOutput(database.DBOutput):
    output: str

    @field_validator("output", mode="before")
    @classmethod
    def b64encode_output(cls, value: bytes | None) -> str:
        if value is None:
            return ""

        return b64encode(value).decode()


@app.post("/jobs", response_model=database.DBJob)
async def create_job(
    request: Request,
    r: JobRequest,
    db_conn: Annotated[database.AsyncConnection, Depends(get_db)],
):
    jobs_defs: dict[str, type[jobs.BaseJob]] = request.app.state.JOBS_DEFS
    if r.name not in jobs_defs:
        raise HTTPException(400, "Job with that name is not defined.")

    job = jobs_defs[r.name].model_validate(r.input)
    is_valid = await job.validate_logic()
    if not is_valid:
        raise HTTPException(400, "Job validation failed")

    return await database.create_job(db_conn, r.name, job.model_dump_json())


@app.get("/jobs/{job_id}", response_model=database.DBJob)
async def get_job_by_id(
    job_id: int, db_conn: Annotated[database.AsyncConnection, Depends(get_db)]
):
    job = await database.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return job


@app.get("/jobs/{job_id}/result", response_model=JobOutput)
async def get_job_result_by_job_id(
    job_id: int, db_conn: Annotated[database.AsyncConnection, Depends(get_db)]
):
    job = await database.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status == jobs.JobStatus.PENDING:
        raise HTTPException(404, "Job is pending")
    if job.status == jobs.JobStatus.IN_PROGRESS:
        raise HTTPException(404, "Job is in progress")
    if job.status == jobs.JobStatus.FAILED:
        raise HTTPException(500, "Job failed")

    job_result = await database.get_job_result_by_job_id(db_conn, job_id)
    if job_result is None:
        raise HTTPException(500, "Job finished, but there's no result")

    return job_result
