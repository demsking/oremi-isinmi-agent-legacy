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
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic import ValidationError

from .core.api import BASE_PATH
from .core.assistant import Assistant
from .core.config import CACHE_DIR
from .core.config import HOST
from .core.config import LOG_FILE
from .core.config import OLLAMA_BASEURL
from .core.config import OLLAMA_MODEL
from .core.config import PORT
from .core.config import ROOT_PATH
from .core.config import USER_AGENT
from .core.controller import Controller
from .core.logger import create_logger
from .core.logger import LOG_LEVEL_STR
from .core.package import APP_NAME
from .core.package import APP_VERSION
from .endpoints.agent import create_agent_endpoints
from .endpoints.docs import create_docs_endpoints
from .endpoints.version import create_version_endpoints


SERVICE_TITLE = 'Oremi Isinmi Agent Documentation'

_current_dir = os.path.dirname(os.path.abspath(__file__))
_readme_path = os.path.realpath(
  os.path.join(_current_dir, '..', 'DOCUMENTATION.md'),
)

with open(_readme_path, encoding='utf-8') as file:
  SERVICE_DESCRIPTION = file.read()

agent_tag = {
  'name': 'Agents Endpoints',
  'description': (
    'Endpoints for managing schedules and triggering events. These endpoints '
    'allow users to create, list, cancel, and trigger schedules. They support '
    'both natural language input and structured data for creating schedules, '
    'providing flexibility for different use cases.'
  ),
}

version_tag = {
  'name': 'Server Endpoints',
  'description': (
    "Endpoints for retrieving server-related metadata, such as the server's "
    'name and version. These endpoints help clients identify the server they '
    'are interacting with and ensure compatibility with the API.'
  ),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
  logger.info(f'Starting {APP_NAME}/{APP_VERSION}')
  logger.info(f'Server Host: {HOST}')
  logger.info(f'Server Port: {PORT}')
  logger.info(f'Server Root Path: {ROOT_PATH}')
  logger.info(f'API Root Path: {ROOT_PATH}')
  logger.info(f'API Base Path: {BASE_PATH}')
  logger.info(f'User Agent: {USER_AGENT}')
  logger.info(f'Cache Directory: {CACHE_DIR}')
  logger.info(f'Ollama URL: {OLLAMA_BASEURL}')
  logger.info(f'Ollama Model: {OLLAMA_MODEL}')
  logger.info(f'Log Level: {LOG_LEVEL_STR}')
  logger.info(f'Log File Path: {LOG_FILE or None}')

  await assistant.load_model()
  yield


api = FastAPI(
  docs_url=None,
  redoc_url=None,
  lifespan=lifespan,
  title=SERVICE_TITLE,
  version=APP_VERSION,
  description=SERVICE_DESCRIPTION,
  root_path=BASE_PATH,
  servers=[
    {'url': BASE_PATH},
  ],
  license_info={
    'name': 'Apache 2.0',
    'url': 'http://www.apache.org/licenses/LICENSE-2.0.html',
  },
  openapi_tags=[
    agent_tag,
    version_tag,
  ],
)

logger = create_logger()

assistant = Assistant(
  model=OLLAMA_MODEL,
  logger=logger,
  ollama_baseurl=OLLAMA_BASEURL,
)

controller = Controller(
  assistant=assistant,
  logger=logger,
)

create_agent_endpoints(tag=agent_tag['name'], api=api, controller=controller)
create_version_endpoints(version_tag['name'], api)
create_docs_endpoints(api)


@api.exception_handler(ValidationError)
async def handle_pydantic_validation_error(
  headers: dict[str, str],
  error: ValidationError,
):
  validation_error = error.errors()[0]

  return JSONResponse(
    status_code=400,
    content={
      'detail': validation_error['msg'],
      'loc': validation_error['loc'],
      'input': str(validation_error['input']),
      'url': validation_error['url'],  # type: ignore
    },
  )


@api.exception_handler(ResponseValidationError)
async def handle_response_validation_error(
  headers: dict[str, str],
  error: ResponseValidationError,
):
  validation_error = error.errors()[0]

  logger.error(validation_error)

  if isinstance(validation_error['input'], BaseModel):
    if isinstance(error.body, list):
      data = [item.model_dump() for item in error.body]
    else:
      data = error.body.model_dump()

    logger.error(data)

    return JSONResponse(content=data)

  return JSONResponse(
    status_code=400,
    content={
      'detail': validation_error['msg'],
    },
  )
