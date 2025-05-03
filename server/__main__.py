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
import asyncio
import json
import os

import uvicorn

from server import api
from server.core.config import HOST
from server.core.config import PORT


def get_log_config() -> dict:
  current_dir = os.path.dirname(os.path.abspath(__file__))
  config_filename = os.path.join(current_dir, 'log-config.json')

  with open(config_filename, encoding='utf-8') as file:
    return json.load(file)


async def main() -> None:
  config = uvicorn.Config(
    app=api,
    host=HOST,
    port=PORT,
    server_header=False,
    use_colors=True,
    proxy_headers=True,
    log_level='info',
    log_config=get_log_config(),
  )

  server = uvicorn.Server(config)
  await server.serve()


if __name__ == '__main__':
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    pass
