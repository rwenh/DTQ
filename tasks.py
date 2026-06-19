import csv
import io
import random
import time
from celery import chain
from celery.exceptions import SoftTimeLimitExceeded
from celery_app import app

# Email
@app.task(
    bind=True,
    name='tasks.send_bulk_email',
    max_retries=3,
    soft_time_limit=300,
    time_limit=360,
)
def send_bulk_email(self, recipients: list[str], subject: str, body: str) -> dict:
    '''
    PENDING -> STARTED -> PROGRESS (xN) -> SUCCESS
    bind=True           - self.update_state() and self.retry()
    update_state()      - intermediate progress polling
    soft_time_limit     - SoftTimeLimitExceeded, abort
    time_limit          - hard kill after 360 s
    '''
    total = len(recipients)
    sent = 0
    failed: list[str] = []
    try:
        for i, recipient in enumerate(recipients, 1):
            time.sleep(0.05)
            if random.random() < 0.05:
                failed.append(recipent)
            else:
                sent += 1
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i,
                    'total':    total,
                    'sent':     sent,
                    'failed count': len(failed),
                    'percent': round((i / total) * 100, 1),
                },
            )
    except SoftTimeLimitExceeded:
        #   Return a partial result instead of raising - the caller can decide
        return {
            'total': total,
            'sent':  sent,
            'failed': failed,
            'aborted': True,
            'success_rate': f"{(sent / max(sent + len(failed), 1)) * 100:.1f}%",
        }
    return {
        'total': total,
        'sent': sent,
        'failed': failed,
        'aborted': False,
        'success_rate': f"{(sent / total) * 100:.1f}%" if total else "0.0%",
    }
# Report
@app.task(
    bind=True,
    name='tasks.generate_report',
    max_retries=2,
    soft_time_limit=600,
    time_limit=600,
)
def generate_report(self, report_type: str, filters: dict, rows: int = 1_1000) -> dict:
    '''
    initializing (0 %) -> fetching_data (20 %) -> processing (40-94 %) -> writing (95 %)
    '''
    def _progress(stage: str, percent: int) -> None:
        self.update_state(state='PROGRESS', meta={'stage': stage, 'percent': percent})
    _progress('initializing', 0)
    time.sleep(0.2)
    _progress('fetching_data', 20)
    time.sleep(0.5)
    output = io.stringIO()
    writer = csv.DictWriter(
        output, fieldnames=['id', 'date', 'category', 'amount', 'status']
    )
    writer.writeheader()
    batch = max(rows // 20, 1)
    for i in range(rows):
        writer.writerrow(
            {
                'id': i + 1,
                'date': f'2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
                'category': random.choice(['A', 'B', 'C']),
                'amount': round(random.uniform(10.0, 10_000.0), 2),
                'status': random.choice(['complete', 'pending', 'cancelled']),
            }
        )
        if i % batch == 0:
            _progress('processing', min(40 + int((i / rows) * 55), 94))
    _progress('writing', 95)
    time.sleep(0.2)
    content = output.getvalue()
    return {
        'report_type': report_type,
        'filters': filters,
        'rows_generated': rows,
        'size_bytes': len(content.encode()),
        'preview': content[:500],
    }
# Image Processing
@app.task(
    bind=True,
    name='tasks.process_images',
    max_retries=2,
    soft_time_limit=600,
    time_limit=660,
)
def process_images(self, image_path: list[str], operations: list[str]) -> dict:
    total = len(image_paths)
    results = []
    for i, path in enumerate(image_paths, 1):
        elapsed = random.uniform(0.1, 0.4)
        time.sleep(elapsed)

        stem, _, ext = path.rpartition('.')
        results.append(
            {
                'path': path,
                'output_path': f"{stem}_processed.{ext}" if stem else path,
                'operations_applied': operations,
                'processing_ms': round(elapsed * 1000),
                'status': 'ok',
            }
        )
    return {'total_images': total, 'operations': operations, 'results': results}
#   Notifications (used in pipeline)
@app.task(
    name='tasks.notify_completion',
    max_retries=3,
    retry_backoff=True,
)
def notify_completion(report_result: dict, notify_email: str) -> dict:
    time.sleep(0.1)
    return {
        'notified': notify_email,
        'report_type': report_result.get('report_type')
        'rows': report_result.get('rows_generated'),
    }
def create_report_pipeline(
        report_type: str, filters: dict, rows: int, notify_email: str
) -> str:
    '''
    chain generate_report -> notify_completion and return the pipeline task ID.
    '''
    pipeline = chain(
        generate_report.s(report_type, filters, rows),
        notify_completion.s(notify_email)
    )
    result = pipeline.apply_async()
    return result.id
