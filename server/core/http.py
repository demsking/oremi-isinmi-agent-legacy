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
import datetime
import urllib.parse
from typing import Any

import hishel
import httpx

from .config import CACHE_DIR
from .config import USER_AGENT
from .logger import logger

__all__ = [
  'HttpClient',
]

_serializer = hishel.PickleSerializer()


class HttpClient(hishel.AsyncCacheClient):
  def __init__(
    self,
    base_url: str = '',
    *,
    headers: dict[str, str] | None = None,
    expire_after: datetime.timedelta | None = None,
    **kwargs,
  ) -> None:
    storage = hishel.AsyncFileStorage(
      ttl=expire_after.seconds if expire_after else 600,
      base_path=CACHE_DIR,
      check_ttl_every=600,  # check every 600s (10m)
      serializer=_serializer,
    )

    _headers = headers or {}
    _headers.update(
      {
        'User-Agent': USER_AGENT,
      }
    )

    super().__init__(
      base_url=base_url,
      headers=_headers,
      storage=storage,
      follow_redirects=True,
      **kwargs,
    )

  @classmethod
  async def check(cls, url: str):
    """
    Check if a URL is reachable.

    Args:
      url (str): The URL to check.

    Returns:
      bool: True if the URL is reachable (status code < 400), False otherwise.
    """
    async with cls() as client:
      try:
        await client.head(url)
        return True
      except Exception:
        return False

  async def request(
    self,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    data: Any | None = None,
    headers: dict[str, str] | None = None,
    **kwargs,
  ) -> httpx.Response:
    url_params = '?' + urllib.parse.urlencode(params) if params else ''
    logger.debug(f'{method} {self.base_url}{url}{url_params} - json={json} - headers={headers}')

    response = await super().request(
      method,
      url,
      params=params,
      json=json,
      data=data,
      headers=headers,
      **kwargs,
    )

    if response.status_code == 422:
      logger.error(response.json())

    response.raise_for_status()

    return response
