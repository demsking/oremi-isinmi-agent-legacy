from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_cancel_schedule_schedules__schedule_id__delete(schedule_id):
  """Cancel Schedule"""
  path = f'/api/api/schedules/{schedule_id}'
  response = client.delete(path)
  assert response.status_code in [200, 404, 204]

