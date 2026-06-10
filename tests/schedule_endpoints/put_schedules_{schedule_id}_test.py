from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_update_schedule_schedules__schedule_id__put(update_schedule_schedules_schedule_id_put_payload, schedule_id):
  """Update Schedule"""
  path = f'/api/schedules/{schedule_id}'
  payload = update_schedule_schedules_schedule_id_put_payload
  response = client.put(path, json=payload)
  assert response.status_code in [200, 404]

