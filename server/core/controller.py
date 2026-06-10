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
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Literal

import dateutil.parser
from fastapi import HTTPException
from fastapi import status
from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import RunContext
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


@dataclass
class AgentDeps:
  controller: 'Controller'
  request: NaturalLanguageRequest
  current_time: datetime
  record: ScheduleRecord | None = None
  records_list: list[ScheduleRecord] | None = None


class AgentResult(BaseModel):
  action: Literal['create', 'read', 'update', 'delete'] = Field(..., description='The resolved CRUD action.')
  id: uuid.UUID | None = Field(None, description='The unique ID of the schedule (for create, update, delete).')
  type: ScheduleType | None = Field(None, description='The type of the schedule if applicable.')
  message: str = Field(..., description='A friendly confirmation or response message for the user.')
  data: ScheduleRecord | list[ScheduleRecord] | None = Field(
    None, description='The payload of the created/updated schedule, or the list of schedules retrieved for read.'
  )


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
        'You are a scheduling assistant.\n'
        "You manage the user's alarms, timers, and reminders using the tools provided.\n"
        'Always query or execute actions using the appropriate tools.'
      ),
      output_type=AgentResult,
    )

    # Register tools
    @self._agent.tool
    async def get_events(ctx: RunContext[AgentDeps]) -> list[ScheduleRecord]:
      """Retrieve all existing schedules/events for the current user."""
      records = await ctx.deps.controller.get_schedule_records(ctx.deps.request.tags, None)
      ctx.deps.records_list = records

      return records

    @self._agent.tool
    async def create_alarm(
      ctx: RunContext[AgentDeps],
      label: str,
      time: str,
      is_recurring: bool = False,
    ) -> ScheduleRecord:
      """Create a new alarm schedule.

      Args:
        label: The description/label for the alarm.
        time: ISO 8601 datetime string specifying when the alarm should trigger.
        is_recurring: Whether this alarm is recurring.
      """
      payload = AlarmPayload(
        label=label,
        time=dateutil.parser.parse(time),
        timezone=ctx.deps.request.timezone,
        is_recurring=is_recurring,
        tags=ctx.deps.request.tags,
      )

      record = await ctx.deps.controller.create_schedule(payload)
      ctx.deps.record = record

      return record

    @self._agent.tool
    async def create_timer(
      ctx: RunContext[AgentDeps],
      label: str,
      duration: str,
    ) -> ScheduleRecord:
      """Create a new timer schedule.

      Args:
        label: The description/label for the timer.
        duration: ISO 8601 duration string (e.g. PT5M).
      """
      payload = TimerPayload(
        label=label,
        timezone=ctx.deps.request.timezone,
        duration=duration,
        is_recurring=False,
        tags=ctx.deps.request.tags,
      )

      record = await ctx.deps.controller.create_schedule(payload)
      ctx.deps.record = record

      return record

    @self._agent.tool
    async def create_reminder(
      ctx: RunContext[AgentDeps],
      label: str,
      time: str,
      is_recurring: bool = False,
    ) -> ScheduleRecord:
      """Create a new reminder schedule.

      Args:
        label: The description/label for the reminder.
        time: ISO 8601 datetime string specifying when the reminder should trigger.
        is_recurring: Whether this reminder is recurring.
      """
      payload = ReminderPayload(
        label=label,
        time=dateutil.parser.parse(time),
        timezone=ctx.deps.request.timezone,
        is_recurring=is_recurring,
        tags=ctx.deps.request.tags,
      )

      record = await ctx.deps.controller.create_schedule(payload)
      ctx.deps.record = record

      return record

    @self._agent.tool
    async def update_alarm(
      ctx: RunContext[AgentDeps],
      schedule_id: uuid.UUID,
      label: str,
      time: str,
      is_recurring: bool = False,
    ) -> ScheduleRecord:
      """Update an existing alarm schedule.

      Args:
        schedule_id: The UUID of the schedule to update.
        label: The new label/description.
        time: ISO 8601 datetime string.
        is_recurring: Whether it is recurring.
      """
      payload = AlarmPayload(
        label=label,
        time=dateutil.parser.parse(time),
        timezone=ctx.deps.request.timezone,
        is_recurring=is_recurring,
        tags=ctx.deps.request.tags,
      )
      record = await ctx.deps.controller.update_schedule(schedule_id, payload)
      record_model = Controller.schedule_to_record(record)
      ctx.deps.record = record_model

      return record_model

    @self._agent.tool
    async def update_timer(
      ctx: RunContext[AgentDeps],
      schedule_id: uuid.UUID,
      label: str,
      duration: str,
    ) -> ScheduleRecord:
      """Update an existing timer schedule.

      Args:
        schedule_id: The UUID of the schedule to update.
        label: The new label/description.
        duration: ISO 8601 duration string (e.g. PT5M).
      """
      payload = TimerPayload(
        label=label,
        timezone=ctx.deps.request.timezone,
        duration=duration,
        is_recurring=False,
        tags=ctx.deps.request.tags,
      )
      record = await ctx.deps.controller.update_schedule(schedule_id, payload)
      record_model = Controller.schedule_to_record(record)
      ctx.deps.record = record_model

      return record_model

    @self._agent.tool
    async def update_reminder(
      ctx: RunContext[AgentDeps],
      schedule_id: uuid.UUID,
      label: str,
      time: str,
      is_recurring: bool = False,
    ) -> ScheduleRecord:
      """Update an existing reminder schedule.

      Args:
        schedule_id: The UUID of the schedule to update.
        label: The new label/description.
        time: ISO 8601 datetime string.
        is_recurring: Whether it is recurring.
      """
      payload = ReminderPayload(
        label=label,
        time=dateutil.parser.parse(time),
        timezone=ctx.deps.request.timezone,
        is_recurring=is_recurring,
        tags=ctx.deps.request.tags,
      )
      record = await ctx.deps.controller.update_schedule(schedule_id, payload)
      record_model = Controller.schedule_to_record(record)
      ctx.deps.record = record_model

      return record_model

    @self._agent.tool
    async def delete_event(
      ctx: RunContext[AgentDeps],
      schedule_id: uuid.UUID,
    ) -> str:
      """Delete an existing schedule/event by its UUID.

      Args:
        schedule_id: The UUID of the schedule to delete.
      """
      await ctx.deps.controller.delete_schedule(schedule_id)
      ctx.deps.record = ScheduleRecord(id=schedule_id, type='alarm', scheduled_time=datetime.now(), label='deleted', tags=[])

      return 'Successfully deleted'

    @self._agent.system_prompt
    def system_prompt(ctx: RunContext[AgentDeps]) -> str:
      current_time_str = ctx.deps.current_time.isoformat()

      return (
        f'You are a scheduling assistant.\n'
        f"The user's timezone is {ctx.deps.request.timezone}.\n"
        f'The current date and time is {current_time_str}.\n'
        f'You can manage alarms, timers, and reminders using the tools provided.\n'
        f'When calling tools that require a datetime string, always format it as a full ISO 8601 string including the correct timezone offset matching the user timezone {ctx.deps.request.timezone}.\n'
        f"If the user asks to list/get events for a specific period (e.g. tomorrow), fetch the events using get_events, then filter them in your response so only events for that period are returned in 'data'.\n"
        f"CRITICAL: You MUST provide your final response by calling the 'final_result' tool. Never write plain text responses to the user directly without calling the 'final_result' tool.\n"
        f"When calling 'final_result':\n"
        f"- 'action' must match the operation performed ('create', 'read', 'update', or 'delete').\n"
        f"- 'id' must be the UUID of the schedule (must be the ID returned by the tool if you created, updated, or deleted a schedule).\n"
        f"- 'type' must be the type of the schedule ('alarm', 'timer', or 'reminder').\n"
        f"- 'message' must be a friendly confirmation message.\n"
        f"- 'data' must NOT be null. For 'create' or 'update', it MUST be the payload used to create/update that schedule (including label, time/duration, timezone, is_recurring, tags). For 'read', it must be the list of schedule records returned by the tool."
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

  async def process_natural_language(self, request: NaturalLanguageRequest) -> AgentResult:
    current_time = get_current_datetime(request.timezone)
    deps = AgentDeps(
      controller=self,
      request=request,
      current_time=current_time,
    )

    try:
      result = await self._agent.run(request.text, deps=deps)
      agent_result: AgentResult = result.output

      if deps.record:
        if not agent_result.action:
          agent_result.action = 'create'

        if not agent_result.id:
          agent_result.id = deps.record.id

        if not agent_result.type:
          agent_result.type = deps.record.type

        if agent_result.action in ('create', 'update') and (
          agent_result.data is None or (isinstance(agent_result.data, dict) and len(agent_result.data) <= 2)
        ):
          agent_result.data = deps.record
      elif deps.records_list is not None:
        if not agent_result.action:
          agent_result.action = 'read'

        if agent_result.action == 'read' and not agent_result.data:
          agent_result.data = deps.records_list

      return agent_result
    except Exception as error:
      self.logger.error(f'Agent error: {error!s}')
      raise HTTPException(status_code=500, detail=f'An unexpected error occurred: {error!s}') from error

  class Response(BaseModel):
    ok: bool
    action: Literal['create', 'read', 'update', 'delete'] | None = Field(
      None, description='The operation handled (create, read, update, delete).'
    )
    id: uuid.UUID | None = Field(..., description='The unique ID of the schedule.')
    type: ScheduleType | None = Field(..., description='Type of scheduled record')
    input: str = Field(..., description='User input that triggered the response')
    message: str | None = Field(..., description='Message generated by the agent to confirm the scheduled action')
    data: ScheduleRecord | SchedulePayload | list[ScheduleRecord] | None = Field(
      ..., description='Data associated with the response'
    )

  class UnknowServiceError(ValueError):
    ...

  class MissingParameterError(ValueError):
    def __init__(self, message: str) -> None:
      self.message = message
