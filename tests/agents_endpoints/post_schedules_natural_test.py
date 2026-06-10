from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')


async def test_handle_agent_message_agent_message_post(handle_agent_message_agent_message_post_payload):
  """Handle Agent Message"""
  path = '/api/agent/message?language=en'
  payload = handle_agent_message_agent_message_post_payload
  response = client.post(path, json=payload)
  assert response.status_code == 201

