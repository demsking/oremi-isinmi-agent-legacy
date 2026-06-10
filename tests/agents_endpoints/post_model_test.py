from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_preload_model_model_post(preload_model_model_post_payload):
  """Preload Model"""
  path = '/api/model?language=fr'
  payload = preload_model_model_post_payload
  response = client.post(path, json=payload)
  assert response.status_code == 200

