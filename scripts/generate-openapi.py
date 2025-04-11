# Copyright 2025 Sébastien Demanou. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Load environment variables from .env file
load_dotenv('.devcontainer/.env')


def generate_openapi():
  from server import api

  client = TestClient(
    api,
    backend='asyncio',
    root_path='',
    follow_redirects=False,
  )

  response = client.get('/openapi.json')

  return response.content


if __name__ == '__main__':
  openapi = generate_openapi().decode('utf-8')

  with open('doc/openapi.json', 'w', encoding='utf-8') as file:
    file.write(openapi)
