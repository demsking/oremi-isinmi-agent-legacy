from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_create_schedule_schedules_post(create_schedule_schedules_post_payload):
  """Create Schedule"""
  path = '/api/schedules'
  payload = create_schedule_schedules_post_payload
  response = client.post(path, json=payload)
  assert response.status_code == 201

