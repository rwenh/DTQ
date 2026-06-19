'''
Patch calery.app.task.task.update_state for the entire test session
'''
from unittest.mock import patch
import pytest
@pytest.fixture(autouse=True)
def mock_task_backend():
    with patch('celery.app.task.Task.update_state'):
        yield
