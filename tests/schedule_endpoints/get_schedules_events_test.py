from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


import pytest

@pytest.mark.skip(reason="Streaming endpoint blocks TestClient")
async def test_stream_schedule_events_schedules_events_get():
  """Stream Schedule Events"""
  path = '/api/schedules/events?tags=%5B%27user%3A9b172e1e-5218-4c95-a786-2c5a1ffeb09c%27%5D'
  response = client.get(path)
  assert response.status_code == 200

