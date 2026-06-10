# Copyright 2025-2026 Sébastien Demanou. All Rights Reserved.
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
import logging
import uuid
from datetime import datetime
from datetime import timedelta

import dateutil.parser
from fastapi import HTTPException
from fastapi import status
from ollama import Options
from ollama import ResponseError
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy import select

from .assistant import Assistant
from .config import TIMEZONE
from .database import async_session
from .engine import Engine
from .engine import SupportedLanguage
from .models import AlarmPayload
from .models import NaturalLanguageRequest
from .models import ReminderPayload
from .models import SchedulePayload
from .models import ScheduleRecord
from .models import ScheduleType
from .models import TimerPayload
from .schema import Schedule
from .time import get_current_datetime


FilterTags = list[str]
ScheduleQueue = asyncio.Queue[ScheduleRecord]


class Controller:
  def __init__(
    self,
    *,
    session_factory=async_session,
    assistant: Assistant,
    logger: logging.Logger,
  ) -> None:
    self.logger = logger

    self._engine_en = Engine('en', logger)
    self._engine_fr = Engine('fr', logger)

    self._session_factory = session_factory
    self._subscribers: set[tuple[tuple[str, ...], ScheduleQueue]] = set()
    self._watcher_task: asyncio.Task | None = None

    self._agent = assistant.create_agent(
      system=(
        'You are a scheduling assistant.\n\n'
        'Always return exactly one well-formed JSON object.\n'
        'Do not add explanations, formatting, or extra text around the JSON.\n'
      )
    )

  def get_engine(self, language: SupportedLanguage) -> Engine:
    return self._engine_fr if language == 'fr' else self._engine_en

  async def create_schedule(self, payload: SchedulePayload) -> ScheduleRecord:
    async with self._session_factory() as session:
      schedule = Schedule(
        type=payload.type,
        label=payload.label,
        timezone=payload.timezone,
        is_recurring=payload.is_recurring,
        tags=payload.tags,
        scheduled_time=payload.time if not isinstance(payload, TimerPayload) else None,
        duration_seconds=payload.duration if isinstance(payload, TimerPayload) else None,
      )

      session.add(schedule)
      await session.commit()
      await session.refresh(schedule)

      return ScheduleRecord(
        id=schedule.id,  # type: ignore
        type=schedule.type.value,
        scheduled_time=schedule.scheduled_time,  # type: ignore
        label=schedule.label,  # type: ignore
        tags=schedule.tags,  # type: ignore
      )

  async def update_schedule(self, schedule_id: uuid.UUID, payload: SchedulePayload) -> Schedule:
    """
    Update an existing schedule with the provided data. Only mutable fields
    will be overwritten; the schedule's ID is immutable.

    The update respects timezone correctness and validates that any new
    datetime fields are properly timezone-aware and in the future when
    required.

    Raises HTTPException 404 if the schedule does not exist.
    """
    async with self._session_factory() as session:
      result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
      schedule = result.scalar_one_or_none()

      if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Schedule not found')

      # Update mutable fields from payload
      schedule.label = payload.label  # type: ignore
      schedule.timezone = payload.timezone  # type: ignore
      schedule.is_recurring = payload.is_recurring  # type: ignore
      schedule.tags = payload.tags  # type: ignore

      if isinstance(payload, TimerPayload):
        schedule.duration = payload.duration
      else:
        # Ensure time is timezone-aware and in future
        if payload.time.tzinfo is None:
          raise HTTPException(status_code=400, detail='Datetime must be timezone-aware')

        if payload.time <= datetime.now(tz=payload.time.tzinfo):
          raise HTTPException(status_code=400, detail='Datetime must be in the future')

        schedule.time = payload.time

      session.add(schedule)
      await session.commit()
      await session.refresh(schedule)

      return schedule

  async def get_due_schedules(self, now: datetime, type_filter: ScheduleType | None = None) -> list[Schedule]:
    async with self._session_factory() as session:
      query = select(Schedule).where((Schedule.scheduled_time <= now) & Schedule.scheduled_time.isnot(None))

      if type_filter:
        query = query.where(Schedule.type == type_filter)

      result = await session.execute(query)

      return result.scalars().all()  # type: ignore

  async def delete_schedule(self, schedule_id: str) -> None:
    async with self._session_factory() as session:
      result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
      schedule = result.scalar_one_or_none()

      if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Schedule not found')

      await session.delete(schedule)
      await session.commit()

  @staticmethod
  def schedule_to_record(schedule: Schedule) -> ScheduleRecord:
    return ScheduleRecord(
      id=schedule.id,  # type: ignore
      type=schedule.type,  # type: ignore
      label=schedule.label,  # type: ignore
      scheduled_time=schedule.scheduled_time,  # type: ignore
      tags=schedule.tags,  # type: ignore
    )

  async def watcher(self) -> None:
    while True:
      now = get_current_datetime(TIMEZONE)
      due = await self.get_due_schedules(now)

      for schedule in due:
        for tags, queue in self._subscribers:
          self.logger.debug(f'Filtering {schedule} against tags {tags}')

          if any(tag in tags for tag in schedule.tags):
            record = Controller.schedule_to_record(schedule)

            await queue.put(record)

        if schedule.is_recurring and schedule.scheduled_time:  # type: ignore
          # For recurring alarms/reminders, add 1 day and update
          next_time = schedule.scheduled_time + timedelta(days=1)
          schedule.scheduled_time = next_time  # type: ignore

          async with self._session_factory() as session:
            session.add(schedule)
            await session.refresh(schedule)
            await session.commit()
        else:
          self.logger.debug(f'Deleting {schedule} from schedule')
          await self.delete_schedule(schedule.id)  # type: ignore

      await asyncio.sleep(1)

  async def register_subscriber(
    self,
    tags: FilterTags,
    queue: ScheduleQueue,
  ) -> None:
    self._subscribers.add((tuple(tags), queue))

  async def unregister_subscriber(
    self,
    tags: FilterTags,
    queue: ScheduleQueue,
  ) -> None:
    self._subscribers.discard((tuple(tags), queue))

  async def start_watcher(self) -> None:
    if self._watcher_task is None or self._watcher_task.done():
      self._watcher_task = asyncio.create_task(self.watcher())

  async def stop_watcher(self) -> None:
    if self._watcher_task and not self._watcher_task.done():
      self._watcher_task.cancel()

      try:
        await self._watcher_task
      except asyncio.CancelledError:
        pass
      finally:
        self._watcher_task = None

  async def get_schedule_records(self, tags: FilterTags, type_filter: ScheduleType | None) -> list[ScheduleRecord]:
    async with self._session_factory() as session:
      statement = select(Schedule)

      if type_filter:
        statement = statement.where((Schedule.type == type_filter))

      result = await session.execute(statement)
      rows = result.scalars().all()

      return [Controller.schedule_to_record(row) for row in rows if any(tag in row.tags for tag in tags)]

  async def process_natural_language(self, request: NaturalLanguageRequest, language: str) -> tuple[str, SchedulePayload]:
    engine = self._engine_en if language == 'en' else self._engine_fr
    _score, retrieved = engine.predict(request.text)

    try:
      result = await self._agent.generate(
        options=Options(temperature=0.2),
        prompt=(
          'Here is an example:\n'
          f'User Request: "{retrieved["input"]}"\n'
          f'JSON Response: {json.dumps(retrieved["output"], indent=2, ensure_ascii=False)}'
          '\n\n'
          'Now for:\n'
          f'{request}\n\n'
          # 'Answer only with a JSON object strictly identical to the above format by just using the user language based on the user request.'
        ),
      )

      self.logger.debug(f'Generated response for "{request.text}": {result.response!s}')

      model = json.loads(result.response)

      if 'type' not in model:
        raise Engine.UnknowServiceError('Unable to identify the appropriate service from the request')

      if model['type'] != 'error' and 'label' not in model:
        raise Engine.UnknowServiceError('Unable to generate a label from the request')

      match model['type']:
        case 'alarm':
          if 'time' not in model:
            raise Engine.UnknowServiceError('Unable to extract a time from the request')

          payload = AlarmPayload(
            label=model['label'],
            time=dateutil.parser.parse(model['time']),
            timezone=request.timezone,
            is_recurring=model.get('is_recurring', False),
            tags=request.tags,
          )

        case 'timer':
          if 'duration' not in model:
            raise Engine.UnknowServiceError('Unable to extract a duration from the request')

          payload = TimerPayload(
            label=model['label'],
            timezone=request.timezone,
            duration=model['duration'],
            is_recurring=model.get('is_recurring', False),
            tags=request.tags,
          )

        case 'reminder':
          if 'time' not in model:
            raise Engine.UnknowServiceError('Unable to extract a time from the request')

          payload = ReminderPayload(
            label=model['label'],
            time=dateutil.parser.parse(model['time']),
            timezone=request.timezone,
            is_recurring=model.get('is_recurring', False),
            tags=request.tags,
          )

        case 'error':
          raise Engine.MissingParameterError(model['message'])

        case _:
          raise Engine.UnknowServiceError(f'Invalid model type: {model["type"]!s}')

      return model['creation_message'], payload
    except ResponseError as error:
      self.logger.error(f'Ollama API error: {error!s}')
      raise HTTPException(status_code=500, detail=f'An unexpected error occurred: {error!s}') from error
    except json.JSONDecodeError as exception:
      self.logger.error(f'Failed to parse natural language: {exception!s}')
      raise HTTPException(status_code=400, detail=f'Could not understand request: {exception!s}') from exception

  class Response(BaseModel):
    ok: bool
    id: uuid.UUID | None = Field(..., description='The unique ID of the schedule.')
    type: ScheduleType | None = Field(..., description='Type of scheduled record')
    input: str = Field(..., description='User input that triggered the response')
    message: str | None = Field(..., description='Message generated by the agent to confirm the scheduled action')
    data: SchedulePayload | None = Field(..., description='Data associated with the response')

  class UnknowServiceError(ValueError):
    ...

  class MissingParameterError(ValueError):
    def __init__(self, message: str) -> None:
      self.message = message
