import json
from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, field_validator


class JobStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


class JobBase(BaseModel):
    id: int
    name: str
    status: JobStatus
    created_at: datetime
    updated_at: Optional[datetime]
    worker: Optional[str]
    processing_time: Optional[int]  # milliseconds


class Job(JobBase):
    input: dict

    @field_validator("input", mode="before")
    @classmethod
    def json_str_output(cls, v: Union[str, dict]) -> dict:
        if isinstance(v, str):
            return json.loads(v)
        return v
