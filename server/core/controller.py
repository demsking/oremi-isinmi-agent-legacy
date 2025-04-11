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
import logging
import uuid
from datetime import datetime

import dateutil.parser
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field

from .assistant import Assistant
from .models import AlarmPayload
from .models import NaturalLanguageRequest
from .models import ReminderPayload
from .models import ScheduleRecord
from .models import ScheduleRequest
from .models import ScheduleType
from .models import TimerPayload
from .models import WebhookResponse


class Controller:
  def __init__(
    self,
    assistant: Assistant,
    logger: logging.Logger,
  ):
    self.logger = logger
    self.scheduler = AsyncIOScheduler()
    self.active_schedules: dict[str, ScheduleRequest] = {}
    self.agent = assistant.create_agent(
      system=(
        'You are a scheduling assistant.\n'
        '\n'
        "Convert the user's scheduling request into a strict JSON object using only\n"
        'the following fields:\n'
        '\n'
        '- "type": must be one of "alarm", "timer", or "reminder"\n'
        '- "time": ISO 8601 datetime (e.g. "2025-04-10T14:00:00Z") — required for\n'
        '  alarms and reminders\n'
        '- "label": a short label or title for the action\n'
        '- "creation_message": a short message confirming the action was created\n'
        '- "duration": ISO 8601 duration (e.g. "PT25M") — required only for timers\n'
        '- "is_recurring": boolean\n'
        '\n'
        'If any required field is missing — for example:\n'
        '- a missing "time" for alarms or reminders\n'
        '- a missing "duration" for timers\n'
        '- no time or duration mentioned in the request at all\n'
        '\n'
        'Then return a valid JSON object with:\n'
        '- "type": set to "error"\n'
        '- "message": a friendly, simple explanation in the user\'s language\n'
        '\n'
        'The error message must:\n'
        '- be short, clear, and conversational\n'
        '- sound like a helpful assistant\n'
        '- never include technical terms or codes\n'
        '\n'
        'Always return exactly one well-formed JSON object.\n'
        'Do not add explanations, formatting, or extra text around the JSON.\n'
      )
    )

  async def call_webhook(self, webhook_url: str, payload: dict) -> WebhookResponse:
    """Call the external webhook with the given payload"""
    try:
      async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(webhook_url, json=payload)
        return WebhookResponse(success=response.is_success, message=response.text, status_code=response.status_code)
    except Exception as exception:
      self.logger.error(f'Webhook call failed: {exception!s}')
      return WebhookResponse(success=False, message=str(exception), status_code=500)

  async def trigger_schedule(self, schedule_id: str):
    """Handle the triggered schedule"""
    schedule = self.active_schedules.get(schedule_id)
    if not schedule:
      self.logger.warning(f'Schedule {schedule_id} not found')
      return

    # Prepare webhook payload
    payload = schedule.webhook_payload or {}
    payload.update(
      {
        'event_type': schedule.type,
        'message': schedule.label,
        'triggered_at': datetime.now().isoformat(),
        'schedule_id': schedule_id,
      }
    )

    # Call webhook
    webhook_response = await self.call_webhook(schedule.webhook_url, payload)

    if webhook_response.success:
      self.logger.info(f'Successfully triggered schedule {schedule_id}')
    else:
      self.logger.error(
        f'Failed to trigger schedule {schedule_id}. Status: {webhook_response.status_code}, Error: {webhook_response.message}'
      )

    # Clean up if not recurring
    if not schedule.is_recurring:
      self.active_schedules.pop(schedule_id, None)

  async def process_natural_language(self, request: NaturalLanguageRequest) -> tuple[str, ScheduleRequest]:
    """Convert natural language to structured schedule request"""
    try:
      result = await self.agent.generate(prompt=str(request), options={'temperature': 0.2})

      self.logger.debug(f'Generated response for "{request.text}": {result.response!s}')

      model = json.loads(result.response)

      if 'type' not in model:
        raise Controller.UnknowServiceError('Unable to identify the appropriate service from the request')

      if model['type'] != 'error' and 'label' not in model:
        raise Controller.UnknowServiceError('Unable to generate a label from the request')

      match model['type']:
        case 'alarm':
          if 'time' not in model:
            raise Controller.UnknowServiceError('Unable to extract a time from the request')

          payload = AlarmPayload(
            label=model['label'],
            time=dateutil.parser.parse(model['time']),
            timezone=request.timezone,
            is_recurring=model.get('is_recurring', False),
            webhook_url='http://example.com',
            webhook_payload=None,
          )

        case 'timer':
          if 'duration' not in model:
            raise Controller.UnknowServiceError('Unable to extract a duration from the request')

          payload = TimerPayload(
            label=model['label'],
            timezone=request.timezone,
            duration=model['duration'],
            is_recurring=model.get('is_recurring', False),
            webhook_url='http://example.com',
            webhook_payload=None,
          )

        case 'reminder':
          if 'time' not in model:
            raise Controller.UnknowServiceError('Unable to extract a time from the request')

          payload = ReminderPayload(
            label=model['label'],
            time=dateutil.parser.parse(model['time']),
            timezone=request.timezone,
            is_recurring=model.get('is_recurring', False),
            webhook_url='http://example.com',
            webhook_payload=None,
          )

        case 'error':
          raise Controller.MissingParameterError(model['message'])

        case _:
          raise Controller.UnknowServiceError(f'Invalid model type: {model["type"]!s}')

      return model['creation_message'], payload
    except json.JSONDecodeError as exception:
      self.logger.error(f'Failed to parse natural language: {exception!s}')
      raise HTTPException(status_code=400, detail=f'Could not understand request: {exception!s}') from exception

  async def schedule(self, schedule: ScheduleRequest) -> ScheduleRecord:
    schedule_id = str(uuid.uuid4())

    # For timers, calculate the trigger time from duration
    if isinstance(schedule, TimerPayload):
      schedule_time = datetime.now() + schedule.duration
    else:
      schedule_time = schedule.time

    # Store the schedule
    self.active_schedules[schedule_id] = schedule

    # Schedule the job
    if isinstance(schedule, AlarmPayload) and schedule.is_recurring:
      self.scheduler.add_job(
        self.trigger_schedule,
        'cron',
        hour=schedule_time.hour,
        minute=schedule_time.minute,
        args=[schedule_id],
        id=schedule_id,
        timezone=schedule.timezone,
      )
    else:
      self.scheduler.add_job(self.trigger_schedule, 'date', run_date=schedule_time, args=[schedule_id], id=schedule_id)

    self.logger.info(f'Created schedule {schedule_id} for {schedule_time}')

    return ScheduleRecord(
      id=schedule_id,
      type=schedule.type,
      label=schedule.label,
      scheduled_time=schedule_time,
      webhook_url=schedule.webhook_url,
    )

  class Response(BaseModel):
    ok: bool
    id: str | None = Field(..., description='The unique ID of the schedule.')
    type: ScheduleType | None = Field(..., description='Type of scheduled record')
    input: str = Field(..., description='User input that triggered the response')
    message: str | None = Field(..., description='Message generated by the agent to confirm the scheduled action')
    data: ScheduleRequest | None = Field(..., description='Data associated with the response')

  class UnknowServiceError(ValueError):
    ...

  class MissingParameterError(ValueError):
    def __init__(self, message: str) -> None:
      self.message = message
