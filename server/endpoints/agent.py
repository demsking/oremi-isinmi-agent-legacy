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

from fastapi import BackgroundTasks
from fastapi import Body
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi.responses import JSONResponse

from ..core.controller import Controller
from ..core.engine import SupportedLanguage
from ..core.models import AlarmPayload
from ..core.models import GenericResponse
from ..core.models import NaturalLanguageRequest
from ..core.models import ScheduleRecord
from ..core.models import ScheduleRequest
from ..core.models import ScheduleType
from ..core.models import TimerPayload
from ..core.spellchecker import SpellChecker


def create_agent_endpoints(
  tag: str,
  api: FastAPI,
  controller: Controller,
) -> None:
  @api.post(
    '/load',
    tags=[tag],
    responses={
      200: {},
    },
  )
  async def load_model(
    language: SupportedLanguage = Query(
      ...,  # Required parameter
      description='The language for which the model should be loaded.',
      examples=['fr', 'en'],
    ),
  ) -> GenericResponse:
    """
    Loads the model for a specific language.

    This endpoint is used to load the necessary model for a given language.
    If the model is not available, an error message is returned.
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
                  'webhook_url': 'https://example.com/webhook',
                  'webhook_payload': {'key': 'value'},
                  'timezone': 'Europe/Paris',
                  'is_recurring': False,
                  'type': 'reminder',
                  'time': datetime.now() + timedelta(hours=1, minutes=25),
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
            'webhook_url': 'https://example.com/webhook',
            'webhook_payload': {'key': 'value'},
            'timezone': 'Europe/Paris',
          }
        )
      ],
    ),
    language: SupportedLanguage | None = Query(
      None,
      description='',
      examples=['en', 'fr'],
    ),
  ) -> Controller.Response:
    """
    Creates a schedule based on natural language input. The input text is
    processed to extract scheduling details, which are then used to create
    a schedule. A webhook URL is required to notify when the schedule
    triggers. Optionally, a payload can be sent with the webhook.

    This endpoint is useful for users who prefer to describe their schedule
    in plain language instead of providing structured data.
    """
    lang = language or SpellChecker.detect_language(request.text)[0]
    engine = controller.get_engine(lang)  # type: ignore

    if engine:
      await engine.load()

    try:
      message, model = await controller.process_natural_language(request, language=lang)
      model.webhook_url = request.webhook_url
      model.webhook_payload = request.webhook_payload
      record = await controller.schedule(model)
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

  @api.post(
    '/schedules',
    tags=[tag],
    responses={
      200: {
        'content': {
          'application/json': {
            'example': ScheduleRecord.model_validate(
              {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'type': 'timer',
                'label': '25-minute timer',
                'scheduled_time': '2025-12-01T10:25:00Z',
                'webhook_url': 'https://example.com/webhook',
                'status': 'scheduled',
              }
            ),
          },
        },
      },
    },
  )
  async def create_schedule(
    schedule: ScheduleRequest = Body(
      ...,
      description='Details of the schedule to create.',
      examples=[
        AlarmPayload.model_validate(
          {
            'label': 'Wake up alarm',
            'time': datetime.now() + timedelta(hours=1, minutes=25),
            'webhook_url': 'https://example.com/webhook',
            'is_recurring': True,
            'timezone': 'UTC',
          }
        ),
        TimerPayload.model_validate(
          {
            'label': '25-minute timer',
            'duration': 'PT25M',
            'webhook_url': 'https://example.com/webhook',
          }
        ),
      ],
    ),
  ) -> ScheduleRecord:
    """
    Creates a new schedule using structured data. The schedule can be a
    one-time event or a recurring event. For timers, the trigger time is
    calculated based on the provided duration. The schedule is stored and
    added to the scheduler for execution.

    This endpoint is ideal for users who have precise scheduling details
    and want to create a schedule programmatically.
    """
    return await controller.schedule(schedule)

  @api.get(
    '/schedules',
    tags=[tag],
    responses={
      200: {
        'content': {
          'application/json': {
            'example': [
              {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'type': 'alarm',
                'scheduled_time': '2025-12-01T10:00:00Z',
                'message': 'Meeting reminder',
                'webhook_url': 'https://example.com/webhook',
                'status': 'scheduled',
              },
            ],
          },
        },
      },
    },
  )
  async def list_schedules(
    type_filter: ScheduleType | None = Query(
      None,
      alias='type',
      description='Filter schedules by type (e.g., alarm, timer).',
      examples=[
        'alarm',
        'timer',
      ],
    ),
    active_only: bool = Query(
      True,
      description='If true, only return schedules that are still active.',
      examples=[
        True,
        False,
      ],
    ),
  ) -> list[ScheduleRecord]:
    """
    Retrieves a list of all active schedules. Users can filter the results
    by schedule type or choose to only include schedules that are still
    active. The schedules are sorted by their scheduled time.

    This endpoint helps users view and manage their existing schedules.
    """
    schedules = [
      ScheduleRecord(
        id=schedule_id,
        type=schedule.type,  # type: ignore
        scheduled_time=schedule.time,  # type: ignore
        label=schedule.label,
        webhook_url=schedule.webhook_url,
        status='scheduled',
      )
      for schedule_id, schedule in controller.active_schedules.items()
      if (not type_filter or schedule.type == type_filter)
      and (not active_only or schedule.time > datetime.now(tz=schedule.time.tzinfo))  # type: ignore
    ]
    return sorted(schedules, key=lambda x: x.scheduled_time)

  @api.delete(
    '/schedules/{schedule_id}',
    tags=[tag],
    responses={
      200: {
        'content': {
          'application/json': {
            'example': {'message': 'Schedule cancelled successfully'},
          },
        },
      },
      404: {
        'content': {
          'application/json': {
            'example': {'detail': 'Schedule not found'},
          },
        },
      },
    },
  )
  async def cancel_schedule(
    schedule_id: str = Path(
      ...,
      description='The unique ID of the schedule to cancel.',
      examples=[
        '123e4567-e89b-12d3-a456-426614174000',
        '987e6543-e21b-34d3-a456-426614174999',
      ],
    ),
  ):
    """
    Cancels a specific schedule by its unique ID. If the schedule is found,
    it is removed from the scheduler and the active schedules list. If the
    schedule does not exist, a 404 error is returned.

    This endpoint is useful for users who want to stop a schedule from
    triggering in the future.
    """
    if schedule_id not in controller.active_schedules:
      raise HTTPException(status_code=404, detail='Schedule not found')

    try:
      controller.scheduler.remove_job(schedule_id)
      controller.active_schedules.pop(schedule_id)
      controller.logger.info(f'Cancelled schedule {schedule_id}')
      return {'message': 'Schedule cancelled successfully'}
    except Exception as exception:
      raise HTTPException(status_code=500, detail=str(exception)) from exception

  @api.post(
    '/schedules/{schedule_id}/trigger',
    tags=[tag],
    responses={
      200: {
        'content': {
          'application/json': {
            'example': {'message': 'Schedule trigger initiated'},
          },
        },
      },
      404: {
        'content': {
          'application/json': {
            'example': {'detail': 'Schedule not found'},
          },
        },
      },
    },
  )
  async def trigger_schedule_now(
    background_tasks: BackgroundTasks,
    schedule_id: str = Path(
      ...,
      description='The unique ID of the schedule to trigger immediately.',
      examples=[
        '123e4567-e89b-12d3-a456-426614174000',
        '987e6543-e21b-34d3-a456-426614174999',
      ],
    ),
  ):
    """
    Immediately triggers a specific schedule by its unique ID. The schedule
    is executed in the background, allowing users to test or manually
    trigger schedules without waiting for their scheduled time.

    This endpoint is helpful for debugging or testing purposes.
    """
    if schedule_id not in controller.active_schedules:
      raise HTTPException(status_code=404, detail='Schedule not found')

    background_tasks.add_task(controller.trigger_schedule, schedule_id)
    return {'message': 'Schedule trigger initiated'}
