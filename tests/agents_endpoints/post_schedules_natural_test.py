from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_create_schedule_from_natural_language_schedules_natural_post(create_schedule_from_natural_language_schedules_natural_post_payload):
  """Create Schedule From Natural Language"""
  path = '/api/schedules/natural?language=en'
  payload = create_schedule_from_natural_language_schedules_natural_post_payload
  response = client.post(path, json=payload)
  assert response.status_code == 201

