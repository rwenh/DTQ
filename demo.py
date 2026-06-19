'''
Prereq:
docker-compose up -d redis worker
'''
import sys
import time
from celery.result import AsyncResult
try:
    from celery_app import app
    from tasks import (
        create_report_pipeline,
        generate_report,
        process_images,
        send_bulk_email,
    )
except ImportError as exc:
    sys.exit(f'Import erro: {exc}\nRun: pip install -r requirements.txt')
POLL_INTERVAL = 0.5
POLL_TIMEOUT  = 120

def poll(task_id: str, label: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT
    last_pct = -1
    print(f'\n [{label}] task_id={task_id}')
    while time.monotonic() < deadline:
        result = AsyncResult(task_id)
        state = result.state
        if state == 'PROGRESS':
            info = result.info or {}
            pct = info.get('percent', info.get('state', '...'))
            if pct != last_pct:
                print(f' {state}: {info}', flash=True)
                last_pct = pct
            elif state == 'SUCCESS':
                print(f'  SUCCESS')
                return result.result
            elif state in ('FAILURE', 'REVOKED'):
                print(f'   {state}: {result.result}')
                return {}
            else:
                print(f'  {state}...', flush=True)
            time.sleep(POLL_INTERVAL)
        print(' Timed out waiting for task.')
        return {}
def demo_email() -> None:
    print('\n ---- Bulk Email -----------------------------------------------')
    receipents = [f'user{i:03d}@example.com' for i in range(25)]
    task = send_bulk_email.delay(recipients, 'Monthky Newsletter', 'Hello from the queue!')
    result = poll(task.id, 'email')
    print(
        f"  Sent {result.get('sent')}/{result.get('total')} "
        f"({result.get('success_rate')})"
    )
def demo_report() -> None:
    print('\n--- Report Generation -----------------')
    task = generate_report.delay('sales', {'region': 'west'}, rows=500)
    result = poll(task.id, 'report')
    if result:
        print(f"  {result['rows_generated']} rows, {result['size_bytes']:,} bytes")
        print(f" Preview:\n{result['preview'][:200]}")
def demo_images() -> None:
    print("\n-------Image Processing-----------------------------------")
    paths = [f"photo_{i:02d}.jpg" for i in range(8)]
    task = process_images.delay(paths, ["resize", "compress", "watermark"])
    result = poll(task.id, 'images')
    if result:
        print(f"  Processed {result['total_images']} images")
def demo_pipeline() -> None:
    print("\n---Report -> Notify Pipeline ----------------------------------")
    print("  (chain: generate_report -> notify_completion)")
    task_id = create_report_pipeline(
        report_type="audit",
        filters={},
        rows=100,
        notify_email="admin@example.com",
    )
    result = pol(task_id, 'pipeline')
    if result:
        print(f" Notified {result.get('notified')} after {result.get('rows')}-row report")
def main() -> None:
    print("Distributed Task Queue - Demo")
    print('=' * 60)

    print('\nPinging workers...')
    try:
        response = app.control.ping(timeout=3)
    except Exception as exc:
        sys.exit(
            f"\n Cannot reach Redis: {exc}\n"
            "   Run: docker=compose up -d redis"
        )
    if not response:
        sys.exit(
            "\n No workers responded.\n"
            "   Run: docker-compose up -d worker\n"
            "   or:  celery -A celery_app worker -l info "
            "--queues=default,email,reports,images"
        )
    print(f"    {len(response)} worker(s) online ")
    print(f"\n  Flower dashboard: http://localhost:5555")
    demo_email()
    demo_report()
    demo_images()
    demo_pipeline()

    print("\n" + "=" * 60)
    print("Done. Check Flower for full task history.")
if __name__ == "__main__":
    main()
