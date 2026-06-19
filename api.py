from fastapi import FastAPI, HTTPException
from celery.result import AsyncResult

from schemas import(
    EmailTaskRequest,
    ImageTaskRequest,
    PipelineRequest,
    ReportTaskRequest,
    TaskStatus,
    TaskSubmission,
)
from tasks import (
    create_report_pipeline,
    generate_report,
    process_images,
    send_bulk_email,
)
app = FastAPI(title='Distributed Task Queue', version='1.0.0')
_TERMINAL_STATES = {'SUCCESS', 'FAILURE', 'REVOKED'}
def _task_status(result: AsyncResult) -> dict:
    '''
    pending - no info yet(.info is None)
    progress- .info holds the meta dict passed to update_state()
    Success - .result holds the return value
    Failure - .result holds the exception instance
    '''
    state = result.state
    if state == 'PENDING':
        return {'task_id': result.id, 'state': state, 'progress': None, 'result': None}
    if state == 'PROGRESS':
        return {'task_id': result.id, 'state': state, 'progress': result.info, 'result': None}
    if state == 'SUCCESS':
        return {'task_id': result.id, 'state': state, 'progress': None, 'result': result.result}
    if state == 'FAILURE':
        return {
            'task_id': result.id,
            'state': state,
            'progress': None,
            'result': None,
            'error': str(result.result),
        }
    # Started , revoked or any custom state
    return {'task_id': result.id, 'state': state, 'progress': result.info, 'result': None}
# Submit endpoints
@app.post('/tasks/email', response_model=TaskSubmission)
def submit_email(req: EmailTaskRequest):
    task = send_bulk_email.delay(req.recipients, req.subject, req.body)
    return {'task_id': task.id, 'state': 'PENDING'}
@app.post('/tasks/report', response_model=TaskSubmission)
def submit_report(req: ReportTaskRequest):
    task = generate_report.delay(req.report_type, req.filters, req.rows)
    return {'task_id': task.id, 'state': 'PENDING'}
@app.post('/tasks/image', response_model=TaskSubmission)
def submit_image(req: ImageTaskRequest):
    task = process_images.delay(req.image_paths, req.operations)
    return {'task_id': task.id, 'state': 'PENDING'}
@app.post('/tasks/pipeline', response_model=TaskSubmission)
def submit_pipeline(req: PipelineRequest):
    '''
    submit a chain : generate_report -> notify_completion.
    '''
    task_id = create_report_pipeline(
        req.report_type, req.filters, req.rows, req.notify_email
    )
    return {'task_id': task_id, 'state': 'PENDING'}
# Status + control
@app.get('/tasks/{task_id}', response_model=TaskStatus)
def get_status(task_id: str):
    return _task_status(AsyncResult(task_id))
@app.delete('/tasks/{task_id}')
def revoke_task(task_id: str, terminate: bool = False):
    '''
    Tasks in a terminal state (success/ failure/ revoked) cannot be revoked.
    '''
    result = AsyncResult(task_id)
    if result.state in _TERMINAL_STATES:
        raise HTTPException(
            status_code=400,
            detail=f'Cannot revoke task in terminal state: {result.state}',
        )
    result.revoke(terminate=terminate)
    return {'task_id': task_id, 'revoked': True, 'terminated': terminate}
