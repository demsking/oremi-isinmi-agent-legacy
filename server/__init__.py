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
from .core.config import EXECUTOR_PROCESSPOOL_SIZE
from .core.config import EXECUTOR_THREADPOOL_SIZE
from .core.config import HOST
from .core.config import JOB_COALESCE
from .core.config import JOB_MAX_INSTANCES
from .core.config import LOG_FILE
from .core.config import LOG_LEVEL
from .core.config import OLLAMA_BASEURL
from .core.config import OLLAMA_MODEL
from .core.config import PORT
from .core.config import ROOT_PATH
from .core.config import STORE_URL
from .core.config import TIMEZONE
from .core.controller import Controller
from .core.database import initialize_database
from .core.logger import create_logger
from .core.package import APP_NAME
from .core.package import APP_VERSION
from .routes.agent import create_agent_endpoints
from .routes.docs import create_docs_endpoints
from .routes.schedule import create_schedule_endpoints
from .routes.version import create_version_endpoints


SERVICE_TITLE = 'Oremi Isinmi Agent Documentation'

_current_dir = os.path.dirname(os.path.abspath(__file__))
_readme_path = os.path.realpath(
  os.path.join(_current_dir, '..', 'DOCUMENTATION.md'),
)

with open(_readme_path, encoding='utf-8') as file:
  SERVICE_DESCRIPTION = file.read()

schedule_tag = {
  'name': 'Schedule Endpoints',
  'description': (
    'Endpoints for managing schedules with structured data. These allow '
    'creating, listing, canceling, and triggering events, giving users full '
    'control over their time-based automation workflows.'
  ),
}

agent_tag = {
  'name': 'Agents Endpoints',
  'description': (
    'Endpoints for natural language interaction and model management. These '
    'include preloading language models and creating schedules from user '
    'input using natural language, enabling intelligent and context-aware '
    'automation.'
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
  logger.info(f'Ollama URL: {OLLAMA_BASEURL}')
  logger.info(f'Ollama Model: {OLLAMA_MODEL}')
  logger.info(f'Store URL: {STORE_URL}')
  logger.info(f'Timezone: {TIMEZONE}')
  logger.info(f'Timezone: {TIMEZONE!r}')
  logger.info(f'ThreadPool Executor Size: {EXECUTOR_THREADPOOL_SIZE!r}')
  logger.info(f'ProcessPool Executor Size: {EXECUTOR_PROCESSPOOL_SIZE!r}')
  logger.info(f'Job Coalesce Enabled: {JOB_COALESCE!r}')
  logger.info(f'Max Job Instances: {JOB_MAX_INSTANCES!r}')
  logger.info(f'Log Level: {LOG_LEVEL}')
  logger.info(f'Log File Path: {LOG_FILE or None}')

  await assistant.load_model()

  logger.info('Initializing database...')
  await initialize_database()

  yield

  logger.info('Shutting down scheduler...')
  await controller.stop_watcher()


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
    schedule_tag,
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

create_schedule_endpoints(schedule_tag['name'], api, controller)
create_agent_endpoints(agent_tag['name'], api, controller)
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
