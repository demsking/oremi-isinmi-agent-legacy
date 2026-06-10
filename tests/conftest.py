# pylint: disable=wildcard-import,unused-wildcard-import,invalid-name,line-too-longimport pytest
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('.devcontainer/.env')


@pytest.fixture
def create_schedule_schedules_post_payload():
  return {
    "label": "Wake up alarm",
    "timezone": "UTC",
    "is_recurring": True,
    "tags": [
      "user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c",
      "device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3"
    ],
    "type": "alarm",
    "time": "2030-06-10T03:31:33.722321+00:00"
  }


@pytest.fixture
def update_schedule_schedules_schedule_id_put_payload():
  return {
    "label": "Drink water",
    "timezone": "UTC",
    "is_recurring": False,
    "tags": [
      "user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c",
      "device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3"
    ],
    "type": "reminder",
    "time": "2030-06-10T03:31:33.854570+00:00"
  }


@pytest.fixture
def schedule_id():
  return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def preload_model_model_post_payload():
  return None


@pytest.fixture
def language():
  return "fr"


@pytest.fixture(autouse=True)
def mock_ollama(monkeypatch):
    import ollama
    
    class MockResponse:
        response = '{"type": "alarm", "label": "test", "time": "2026-06-10T03:31:33Z", "creation_message": "test"}'
    
    async def mock_generate(*args, **kwargs):
        return MockResponse()
    
    monkeypatch.setattr(ollama.AsyncClient, "generate", mock_generate)
    
@pytest.fixture
def create_schedule_from_natural_language_schedules_natural_post_payload():
  return {
    "text": "Set a reminder for a meeting at 10 AM tomorrow.",
    "timezone": "Europe/Paris",
    "tags": [
      "user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c",
      "device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3"
    ]
  }

