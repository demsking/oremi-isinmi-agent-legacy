from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_get_server_info_server_get():
  """Get Server Info"""
  path = '/api/server'
  response = client.get(path)
  assert response.status_code == 200

