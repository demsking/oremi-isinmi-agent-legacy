from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_list_schedules_schedules_get():
  """List Schedules"""
  path = '/api/api/schedules?tags=%5B%27user%3A9b172e1e-5218-4c95-a786-2c5a1ffeb09c%27%5D&type=alarm'
  response = client.get(path)
  assert response.status_code in [200, 422, 404]

