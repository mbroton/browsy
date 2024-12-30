import os
from contextlib import asynccontextmanager
from typing import Annotated, Optional
from base64 import b64encode
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from browsy import _database, _jobs, __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("BROWSY_DB_PATH")
    if not db_path:
        raise ValueError("BROWSY_DB_PATH not set")

    jobs_path = os.environ.get("BROWSY_JOBS_PATH", str(Path().absolute()))

    app.state.DB_PATH = db_path
    app.state.JOBS_DEFS = _jobs.collect_jobs_defs(jobs_path)

    conn = await _database.create_connection(db_path)

    try:
        await _database.init_db(conn)
    finally:
        await conn.close()

    yield


app = FastAPI(
    lifespan=lifespan,
    title="browsy",
    version=__version__,
    redoc_url=None,
    openapi_tags=[
        {
            "name": "jobs",
            "description": (
                "Create, monitor, and retrieve results from browser"
                " automation jobs."
            ),
        }
    ],
)


async def get_db(request: Request):
    conn = await _database.create_connection(request.app.state.DB_PATH)

    try:
        yield conn
    finally:
        await conn.close()


class JobRequest(BaseModel):
    name: str
    input: dict


class JobOutput(_database.DBOutput):
    output: str

    @field_validator("output", mode="before")
    @classmethod
    def b64encode_output(cls, value: Optional[bytes]) -> str:
        if value is None:
            return ""

        return b64encode(value).decode()


@app.get("/health", include_in_schema=False)
async def healthcheck(_: Annotated[_database.AsyncConnection, Depends(get_db)]):
    return {"status": "ok", "version": __version__}


@app.post("/api/v1/jobs", response_model=_database.DBJob, tags=["jobs"])
async def submit_job(
    request: Request,
    r: JobRequest,
    db_conn: Annotated[_database.AsyncConnection, Depends(get_db)],
):
    jobs_defs: dict[str, type[_jobs.BaseJob]] = request.app.state.JOBS_DEFS
    if r.name not in jobs_defs:
        raise HTTPException(400, "Job with that name is not defined.")

    job = jobs_defs[r.name].model_validate(r.input)
    is_valid = await job.validate_logic()
    if not is_valid:
        raise HTTPException(400, "Job validation failed")

    return await _database.create_job(db_conn, r.name, job.model_dump_json())


@app.get("/api/v1/jobs/{job_id}", response_model=_database.DBJob, tags=["jobs"])
async def get_job_by_id(
    job_id: int, db_conn: Annotated[_database.AsyncConnection, Depends(get_db)]
):
    job = await _database.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return job


@app.get(
    "/api/v1/jobs/{job_id}/result", response_model=JobOutput, tags=["jobs"]
)
async def get_job_result_by_job_id(
    job_id: int, db_conn: Annotated[_database.AsyncConnection, Depends(get_db)]
):
    job = await _database.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status == _jobs.JobStatus.PENDING:
        raise HTTPException(404, "Job is pending")
    if job.status == _jobs.JobStatus.IN_PROGRESS:
        raise HTTPException(404, "Job is in progress")
    if job.status == _jobs.JobStatus.FAILED:
        raise HTTPException(500, "Job failed")

    job_result = await _database.get_job_result_by_job_id(db_conn, job_id)
    if job_result is None:
        raise HTTPException(500, "Job finished, but there's no result")

    return job_result
