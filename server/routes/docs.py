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
import json

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from ..core.api import parse_path


def create_docs_endpoints(api: FastAPI) -> None:
  # Get the OpenAPI JSON content from FastAPI
  def get_openapi_json():
    openapi_schema = get_openapi(
      title=api.title,
      version=api.version,
      description=api.description,
      routes=api.routes,
      tags=api.openapi_tags,
      servers=api.servers,
      contact=api.contact,
      license_info=api.license_info,
      terms_of_service=api.terms_of_service,
    )
    return jsonable_encoder(openapi_schema)

  docs_path = parse_path('/docs')
  openapi_content = get_openapi_json()
  openapi_json_content = json.dumps(openapi_content)

  @api.get('/', include_in_schema=False)
  async def redirect_to_docs():
    return HTMLResponse(status_code=307, headers={'Location': docs_path})

  @api.get(docs_path, response_class=HTMLResponse, include_in_schema=False)
  async def html_documentation():
    return f"""
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8"/>
          <title>Oremi Isinmi Agent Documentation</title>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            .open-api-client-button {{
              display: none !important;
            }}
          </style>
        </head>
        <body>
          <script id="api-reference" type="application/json">{openapi_json_content}</script>
          <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
        </body>
      </html>
    """
