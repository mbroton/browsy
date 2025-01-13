import os
import importlib.resources as resources
from contextlib import asynccontextmanager
from typing import Annotated, Optional
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from browsy import _database, _jobs, __version__
from browsy import __name__ as pkg_name

_JOBS_DEFS = _jobs.collect_jobs_defs(
    os.environ.get("BROWSY_JOBS_PATH", str(Path().absolute()))
)


def custom_openapi():
    """Custom OpenAPI to include jobs in schema that are dynamically loaded."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for _, job_cls in _JOBS_DEFS.items():
        openapi_schema["components"]["schemas"][
            job_cls.__name__
        ] = job_cls.model_json_schema()
    app.openapi_schema = openapi_schema
    return app.openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("BROWSY_DB_PATH")
    if not db_path:
        raise ValueError("BROWSY_DB_PATH not set")

    app.state.DB_PATH = db_path
    app.state.startup_time = datetime.now(timezone.utc)

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
app.openapi = custom_openapi

template_dir = resources.files(pkg_name) / "templates"
templates = Jinja2Templates(directory=template_dir)


async def get_db(request: Request):
    conn = await _database.create_connection(request.app.state.DB_PATH)

    try:
        yield conn
    finally:
        await conn.close()


class JobRequest(BaseModel):
    name: str
    parameters: dict


@app.post("/api/v1/jobs", response_model=_database.DBJob, tags=["jobs"])
async def submit_job(
    r: JobRequest,
    db_conn: Annotated[_database.AsyncConnection, Depends(get_db)],
):
    if r.name not in _JOBS_DEFS:
        raise HTTPException(400, "Job with that name is not defined.")

    job = _JOBS_DEFS[r.name].model_validate(r.parameters)
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


@app.get("/api/v1/jobs/{job_id}/result", tags=["jobs"])
async def get_job_result_by_job_id(
    job_id: int, db_conn: Annotated[_database.AsyncConnection, Depends(get_db)]
):
    job = await _database.get_job_by_id(db_conn, job_id)
    if not job:
        raise HTTPException(404)

    headers = {
        "X-Job-Status": job.status,
        "X-Job-Last-Updated": job.updated_at.isoformat(),
    }

    if job.status in (_jobs.JobStatus.IN_PROGRESS, _jobs.JobStatus.PENDING):
        return Response(202, headers=headers)

    if job.status == _jobs.JobStatus.FAILED:
        return Response(204, headers=headers)

    job_result = await _database.get_job_result_by_job_id(db_conn, job_id)
    if job_result is None:
        return Response(204, headers=headers)

    return Response(
        content=job_result,
        status_code=200,
        media_type="application/octet-stream",
        headers=headers,
    )


@app.get("/health", include_in_schema=False)
async def healthcheck(_: Annotated[_database.AsyncConnection, Depends(get_db)]):
    return {"status": "ok", "version": __version__}


@app.get("/internal", include_in_schema=False)
async def get_monitoring():
    return RedirectResponse(url="/internal/workers")


@app.get("/internal/workers", include_in_schema=False)
async def get_workers_information(
    request: Request,
    db_conn: Annotated[_database.AsyncConnection, Depends(get_db)],
):
    workers = await _database.get_workers(
        db_conn, last_activity_time_ge=app.state.startup_time
    )
    return templates.TemplateResponse(
        request=request, name="workers.html", context={"workers": workers}
    )


@app.get("/internal/jobs", include_in_schema=False)
async def get_jobs_information(
    request: Request,
    db_conn: Annotated[_database.AsyncConnection, Depends(get_db)],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
):
    jobs, count = await _database.get_jobs(db_conn, limit=limit, offset=offset)
    for j in jobs:
        j.status = j.status.value
    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "jobs": jobs,
            "pagination": {"limit": limit, "offset": offset, "count": count},
        },
    )
