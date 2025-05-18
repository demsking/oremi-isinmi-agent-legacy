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
from datetime import datetime
from datetime import timedelta

from fastapi import Body
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import JSONResponse

from ..core.controller import Controller
from ..core.engine import SupportedLanguage
from ..core.models import GenericResponse
from ..core.models import NaturalLanguageRequest
from ..core.spellchecker import SpellChecker


def create_agent_endpoints(tag: str, api: FastAPI, controller: Controller) -> None:
  @api.post(
    '/model',
    tags=[tag],
    responses={
      200: {},
    },
  )
  async def preload_model(
    language: SupportedLanguage = Query(
      ...,
      description='The language for which the model should be loaded.',
      examples=['fr', 'en'],
    ),
  ) -> GenericResponse:
    """
    Preload a language model.

    Use this endpoint to proactively load the model for a given language. This
    reduces the response latency for the first natural language request by
    preparing the engine in advance.

    The model will be initialized if not already loaded. If already active,
    the call has no adverse effect.
    """
    engine = controller.get_engine(language)

    await engine.load()

    return GenericResponse(ok=True)

  @api.post(
    '/schedules/natural',
    tags=[tag],
    status_code=201,
    response_model=Controller.Response,
    responses={
      201: {
        'content': {
          'application/json': {
            'example': Controller.Response.model_validate(
              {
                'ok': True,
                'id': 'd420613a-34a9-4224-8907-117551515099',
                'type': 'reminder',
                'input': 'Set a reminder for a meeting at 10 AM tomorrow.',
                'message': 'Reminder created for meeting with John.',
                'data': {
                  'label': 'Meeting with John',
                  'timezone': 'Europe/Paris',
                  'is_recurring': False,
                  'type': 'reminder',
                  'time': datetime.now() + timedelta(hours=1, minutes=25),
                  'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
                },
              }
            ),
          },
        },
      },
      412: {
        'content': {
          'title': 'Missing required information to create the schedule',
          'application/json': {
            'example': Controller.Response.model_validate(
              {
                'ok': False,
                'id': None,
                'type': None,
                'input': 'Set a reminder.',
                'message': 'You need to specify when you want to be reminded.',
                'data': None,
              }
            ),
          },
        },
      },
      400: {
        'content': {
          'application/json': {},
        },
      },
    },
  )
  async def create_schedule_from_natural_language(
    request: NaturalLanguageRequest = Body(
      ...,
      description='A natural language request to create a schedule.',
      examples=[
        NaturalLanguageRequest.model_validate(
          {
            'text': 'Set a reminder for a meeting at 10 AM tomorrow.',
            'timezone': 'Europe/Paris',
            'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
          }
        )
      ],
    ),
    language: SupportedLanguage | None = Query(
      None,
      description='Optional language code to assist natural language parsing (e.g., "en" for English, "fr" for French).',
      examples=['en', 'fr'],
    ),
  ) -> Controller.Response:
    """
    Create a schedule from a natural language request.

    This endpoint interprets natural language input to generate a structured
    schedule such as a reminder or timed event. For example, users can say
    "Set a reminder for a meeting at 10 AM tomorrow" and the system will
    parse and create the corresponding schedule.

    The request body must include:
    - `text`: the natural language instruction
    - `tags`: at least one user and one device tag
    - `timezone`: required for proper scheduling

    Optionally, the `language` query can help fine-tune parsing logic.

    Returns a successful response if the schedule is created, or 412 if
    required information (like time) is missing from the input.
    """
    lang = language or SpellChecker.detect_language(request.text)[0]
    engine = controller.get_engine(lang)  # type: ignore

    if engine:
      await engine.load()

    try:
      message, model = await controller.process_natural_language(request, language=lang)
      record = await controller.create_schedule(model)
      response = Controller.Response(
        ok=True,
        id=record.id,
        type=record.type,
        input=request.text,
        message=message,
        data=model,
      )

      return JSONResponse(
        status_code=201,
        content=response.model_dump(),
      )  # type: ignore
    except Controller.MissingParameterError as error:
      response = Controller.Response(
        ok=False,
        id=None,
        type=None,
        input=request.text,
        message=error.message,
        data=None,
      )

      return JSONResponse(
        status_code=412,
        content=response.model_dump(),
      )  # type: ignore
    except Controller.UnknowServiceError as error:
      raise HTTPException(status_code=400, detail=str(error)) from error
