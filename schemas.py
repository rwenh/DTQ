from typing import Any
from pydantic import BaseModel, Field
#   Requests
class EmailTaskRequest(BaseModel):
    recipients: list[str] = Field(..., min_length=1, max_length=10_000)
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
class ReportTaskRequest(BaseModel):
    report_type: str = Field(..., pattern=r'^(sales|inventory|users|audit)$')
    filters: dict[str, Any] = Field(default_factory=dict)
    rows: int = Field(default=1_000, ge=1, le=100_000)
class ImageTaskRequest(BaseModel):
    image_paths: list[str] = Field(..., min_length=1, max_length=500)
    operations: list[str] = Field(..., min_length=1)
class PipelineRequest(BaseModel):
    report_type: str = Field(..., pattern=r'^(sales|inventory|users|audit)$')
    filters: dict[str, Any] = Field(default_factory=dict)
    rows: int = Field(default=1_000, ge=1, le=100_000)
    notify_email: str = Field(..., min_length=3)
# Responses
class TaskSubmission(BaseModel):
    '''Returned immediately on task submit - the client uses task_id to poll'''
    task_id: str
    state: str
class TaskStatus(BaseModel):
    '''Returned by the status endpoint; shape varies by state.'''
    task_id: str
    state: str
    progress: dict | None = None    # PROGRESS / STARTED
    result: Any = None              # Success
    error: str | None = None        # Failure
