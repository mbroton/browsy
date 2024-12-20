from contextlib import asynccontextmanager
from typing import Annotated
from base64 import b64encode

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator

from app import data


@asynccontextmanager
async def lifespan(*_):
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


class JobRequestBase(BaseModel):
    type: data.JobType


class URLJobRequest(JobRequestBase):
    url: HttpUrl


class HTMLJobRequest(JobRequestBase):
    html: str


class JobOutput(data.DBOutput):
    output: str

    @field_validator("output", mode="before")
    @classmethod
    def b64encode_output(cls, value: bytes | None) -> str:
        if value is None:
            return ""

        return b64encode(value).decode()


@app.post("/job", response_model=data.DBJob)
async def create_job(
    r: URLJobRequest | HTMLJobRequest,
    db_conn: Annotated[data.AsyncConnection, Depends(get_db)],
):
    if isinstance(r, URLJobRequest):
        job = await data.create_job(
            db_conn, r.type, data.JobSourceType.URL, str(r.url)
        )

    elif isinstance(r, HTMLJobRequest):
        job = await data.create_job(
            db_conn, r.type, data.JobSourceType.HTML, r.html
        )
    else:
        raise HTTPException(400)

    return job


@app.get("/job/{job_id}", response_model=data.DBJob)
async def get_job_by_id(
    job_id: int, db_conn: Annotated[data.AsyncConnection, Depends(get_db)]
):
    job = await data.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return job


@app.get("/job/{job_id}/result")
async def get_job_result_by_job_id(
    job_id: int, db_conn: Annotated[data.AsyncConnection, Depends(get_db)]
):
    job = await data.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status in (data.JobStatus.PENDING, data.JobStatus.IN_PROGRESS):
        raise HTTPException(404, "Job is not finished yet")
    if job.status == data.JobStatus.FAILED:
        raise HTTPException(500, "Job failed")

    job_result = await data.get_job_result_by_job_id(db_conn, job_id)
    if job_result is None:
        raise HTTPException(500, "Job finished, but there's no result")

    return job_result
