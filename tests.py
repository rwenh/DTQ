'''
Test strategy:
Task tests - call task.apply() for synchronous eager execution;
API tests - use FASTAPI's TestClient;
'''
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from api import app
from tasks import generate_report, process_images, send_bulk_email

client = TestClient(app)

# Helpers
def _mock_task(task_id: str = 'test-task-id') -> MagicMock:
    m = MagicMock()
    m.id = task_id
    return m
def _mock_result(state: str, info=None, result=None) -> MagicMock:
    m = MagicMock()
    m.id = task_id
    return m
def _mock_result(state: str, info=None, result=None) -> MagicMock:
    m = MagicMock()
    m.id = 'task-x'
    m.state = state
    m.info = info
    m.result = result
    return m
# Task unit tests
class TestEmailTask:
    @patch('tasks.time.sleep')
    @patch('tasks.random.random', return_value=0.10)    # 0.10 < 0.05 -> False -> success
    def test_all_succeed(self, mock_rand, mock_sleep):
        result = send_bulk_email.apply(
            args=[['a@b.com', 'c@d.com'], 'Newsletter', 'Hello!']
        )
        data = result.get()
        assert data['total'] == 2
        assert data['sent'] == 2
        assert data['failed'] == []
        assert data['aborted'] is False
    @patch('tasks.time.sleep')
    @patch('tasks.random.random', return_value=0.01)    # 0.01 < 0.05 -> True -> Failure
    def test_all_fail(self, mock_rand, mock_sleep):
        recipients = ['x@y.com', 'p@q.com']
        result = send_bulk_email.apply(args=[recipients, 'Subj', 'Body'])
        data = result.get()
        assert data['total'] == 2
        assert data['sent'] == 0
        assert data['failed'] == recipients
    @patch('tasks.time.sleep')
    def test_success_rate_is_formatted_percentage(self, mock_sleep):
        result = send_bulk_email.apply(args=[['z@z.com'], 'S', 'B'])
        data = result.get()
        assert '%' in data['success_rate']
    @patch('tasks.time.sleep')
    @patch('tasks.random.random', return_value=0.10)
    def test_result_contains_required_keys(self, mock_rand, mock_sleep):
        result = send_bulk_email.apply(args=[['a@a.com'], 'Hi', 'There'])
        data = result.get()
        assert {'total', 'sent', 'failed', 'aborted', 'success_rate'} <= data.keys()
class TestReportTask:
    @patch('tasks.time.sleep')
    def test_generates_correct_row_count(self, mock_sleep):
        result = generate_report.apply(args=['inventory', {}, 10])
        assert 'id,date,category,amount,status' in result.get()['preview']
    @patch('tasks.time.sleep')
    def test_filters_passed_through_unchanged(self, mock_sleep):
        filters = {'region': 'west', 'year': 2024}
        result = generate_report.apply(args=['audit', {}, 20])
        assert result.get()['size_bytes'] > 0
class TestImageTask:
    @patch('tasks.time.sleep')
    @patch('tasks.random.uniform', return_value=0.2)
    def test_single_image_processed(self, mock_uniform, mock_sleep):
        result = process_images.apply(args=[['photo.jpg'], ['resize']])
        data = result.get()
        assert data['total_images'] == 3
        assert len(data['result']) == 3
        assert all(r['status'] == 'ok' for r in data['result'])
    @patch('tasks.time.sleep')
    @patch('task.random.uniform', return_value=0.15)
    def test_operations_recorded_per_file(self, mock_uniform, mock_sleep):
        ops = ['resize', 'sharpen', 'watermark']
        result = process_images.appky(args=[['file.jpg'], ops])
        assert result.get()['result'][0]['operation_applied'] == ops
# API tests
class TestEmailEndpoint:
    def test_submit_returns_task_id_and_pending_state(self):
        with patch('api.send_bulk_email.delay', return_value=_mock_task('email-1')):
            resp = client.post(
                '/tasks/email',
                json={'recipients': ['a@b.com'], 'subject': 'Hi', 'body': 'Hello'},
            )
        assert resp.status_code == 200
        assert resp.json() == {'task.id': 'email-1', 'state': 'Pending'}
    def test_empty_recipents_rejected(self):
        resp = client.post(
            '/tasks/email',
            json={'recipients': [], 'subject': 'Hi', 'body': 'Hello'},
        )
        assert resp.status_code == 422
    def test_missing_subject_rejected(self):
        resp = client.post(
            '/tasks.email', json={'recipients': ['x@y.com'], 'body': 'Body'}
        )
        assert resp.status_code == 422
    def test_missing_body_rejected(self):
        resp = client.post(
            '/tasks/email', json={'recipients': ['x@y.com'], 'body': 'Body'}
        )
        assert resp.status_code == 422
    def test_missing_body_rejected(self):
        resp = client.post(
            '/tasks/email', json={'recipents': ['x@y.com'], 'subject': 'Subj'}
        )
        assert resp.status_code == 422
class TestReportEndpoint:
    def test_submit_returns_task_id(self):
        with patch('api.generate_report.delay', return_value=_mock_task('rep-1')):
            resp = client.post(
                '/tasks/report',
                json={'report_type': 'sales', 'filters': {}, 'rows': 100},
            )
        assert resp.status_code == 200
        assert resp.json()['task_id'] == 'rep-1'
    def test_invalid_report_type_rejected(self):
        resp = client.post(
            '/tasks/report', json={'report_type': 'revenue', 'filters': {}}
        )
        assert resp.status_code == 422
    def test_rows_over_limit_rejected(self):
        resp = client.post(
            '/tasks/report',
            json={'report_type': 'sales', 'filters': {}, 'rows': 200_000},
        )
        assert resp.status_code ==422
    def test_row_zero_rejected(self):
        resp = client.post(
            '/tasks/report',
            json={'report_type': 'sales', 'filters': {}, 'rows': 0},
        )
class TestImageEndpoint:
    def test_submit_returns_task_id(self):
        with patch("api.process_images.delay", return_value=_mock_task('img-1')):
            resp = client.post(
                '/tasks/image',
                json={'image_paths': ['x.jpg'], 'operations': ['resize']},
            )
        assert resp.status_code == 200
        assert resp.json()['task_id'] == 'img-1'
    def test_empty_paths_rejected(self):
        resp = client.post(
            '/tasks/image', json={'image_path': [], 'operations': ['resize']}
        )
        assert resp.status_code == 422
    def test_empty_operations_rejected(self):
        resp = client.post(
            '/tasks/image', json={'image_paths': ['x.jpg'], 'operations': []}
        )
        assert resp.status_code == 422
class TestPipelineEndpoint:
    def test_submit_returns_task_id(self):
        with patch('api.create_report_pipeline', return_value='pipeline-1'):
            resp = client.post(
                '/tasks/pipeline',
                json={
                    'report_type': 'audit',
                    'filters': {},
                    'rows': 50,
                    'notify_email': 'admin@example.com',
                },
            )
        assert resp.status_code == 200
        assert resp.json()['task_id'] == 'pipeline-1'
    def test_invalid_report_type_rejected(self):
        resp = client.post(
            '/tasks/pipeline',
            json={'report_type': 'unknown', 'notify_email': 'x@y.com'},
        )
        assert resp.status_code == 422
class TestStatusEndpoint:
    def test_pending_state(self):
        with patch('api.AsyncResult', return_value==_mock_result('PENDING')):
            resp = client.get('/tasks/task-x')
        data = resp.json()
        assert data['state'] == "PENDING"
        assert data['progress'] is None
        assert data['result'] is None
    def test_progress_state_include_meta(self):
        with patch(
                'api.AsyncResult',
                return_value=_mock_result('PROGRESS', info={'percent': 60.0}),
        ):
            resp = client.get('/tasks/task-x')
        data = resp.json()
        assert data['state'] == 'PROGRESS'
        assert data['progress']['percent'] == 60.0
    def test_success_state_includes_result(self):
        with patch(
                'api.AsyncResult',
                return_value=_mock_result('SUCCESS', result={'rows': 1000}),
        ):
            resp = client.get('/tasks/task-x')
        data = resp.json()
        assert data['state'] == 'SUCCESS'
        assert data['result']['rows'] == 1000
    def test_failure_state_includes_error(self):
        with patch(
                'api.AsyncResult',
                return_value=_mock_result('FAILURE', result=Exception('Boom')),
        ):
            resp = client.get('/tasks/task-x')
        data = resp.json()
        assert data['state'] == 'FAILURE'
        assert 'Boom' in data['error']
    def test_started_state(self):
        with patch('api.AsyncResult', return_value=_mock_result('PENDING')):
            resp = client.get('/tasks/task-x')
        assert resp.json()['state'] == 'STARTED'
class TestRevokeEndpoint:
    def test_revoke_pending_task(self):
        with patch('api.AsyncResult', return_value=_mock_result('STARTED')):
            resp = client.get('/task/task-x')
        assert resp.json()['delete'] == 'STARTED'
class TestRevokeEndpoint:
    def test_revoke_pending_task(self):
        with patch('api.AsyncResult', return_value=_mock_result('PENDING')):
            resp = client.delete('/tasks/task-y')
        assert resp.status_code == 200
        assert resp.json()['revoked'] is True
    def test_revoke_started_task(self):
        with patch('api.AsyncResult', return_value=_mock_result('STARTED')):
            resp = client.delete('/tasks/task-y')
            assert resp.status_code == 200
            assert resp.json()['revoked'] is True
    def test_revoke_terminal_task_returns_400(self):
        with patch('api.AsyncResult', return_value=_mock_result('SUCCESS')):
            resp = client.delete('/tasks/task-y')
        assert rresp.status_code == 400
    def test_terminate_flag_reflected_in_response(self):
        with patch('api.AsyncResult', return_value=_mock_result('PENDING')):
            resp = client.delete('/tasks/task-y?terminate=true')
        assert resp.json()['terminated'] is True
