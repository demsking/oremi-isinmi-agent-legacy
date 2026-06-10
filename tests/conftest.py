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
    from pydantic_ai import Agent
    from server.core.controller import AgentResult
    from server.core.models import AlarmPayload
    from datetime import datetime, timezone
    
    class MockResponse:
        response = '{"action": "create", "type": "alarm", "label": "test", "time": "2026-06-10T03:31:33Z", "creation_message": "test"}'
    
    async def mock_generate(*args, **kwargs):
        return MockResponse()
        
    async def mock_pull(*args, **kwargs):
        return None
        
    class MockRunResult:
        def __init__(self):
            self.output = AgentResult(
                action="create",
                id="d420613a-34a9-4224-8907-117551515099",
                type="alarm",
                message="Alarm created for 10 AM tomorrow.",
                data=AlarmPayload(
                    label="test",
                    time=datetime(2030, 6, 11, 10, 0, 0, tzinfo=timezone.utc),
                    timezone="Europe/Paris",
                    is_recurring=False,
                    tags=["user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c"]
                )
            )
            self.data = self.output
            
    async def mock_run(*args, **kwargs):
        return MockRunResult()
    
    monkeypatch.setattr(ollama.AsyncClient, "generate", mock_generate)
    monkeypatch.setattr(ollama.AsyncClient, "pull", mock_pull)
    monkeypatch.setattr(Agent, "run", mock_run)
    
@pytest.fixture
def handle_agent_message_agent_message_post_payload():
  return {
    "text": "Set a reminder for a meeting at 10 AM tomorrow.",
    "timezone": "Europe/Paris",
    "tags": [
      "user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c",
      "device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3"
    ]
  }
