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
from collections.abc import AsyncGenerator
from datetime import datetime
from datetime import timedelta
from uuid import UUID

from fastapi import Body
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse

from ..core.controller import Controller
from ..core.controller import ScheduleQueue
from ..core.models import AlarmPayload
from ..core.models import BaseSchedulePayload
from ..core.models import GenericResponse
from ..core.models import ReminderPayload
from ..core.models import SchedulePayload
from ..core.models import ScheduleRecord
from ..core.models import ScheduleType
from ..core.models import TimerPayload
from server.core.schema import Schedule


def create_schedule_endpoints(tag: str, api: FastAPI, controller: Controller) -> None:
  @api.post(
    '/schedules',
    tags=[tag],
    status_code=201,
    responses={
      201: {
        'content': {
          'application/json': {
            'example': ScheduleRecord.model_validate(
              {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'type': 'timer',
                'label': '25-minute timer',
                'scheduled_time': '2025-12-01T10:25:00Z',
                'status': 'scheduled',
                'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
              }
            ),
          },
        },
      },
    },
  )
  async def create_schedule(
    schedule: SchedulePayload = Body(
      ...,
      description='Details of the schedule to create.',
      examples=[
        AlarmPayload.model_validate(
          {
            'label': 'Wake up alarm',
            'time': datetime.now() + timedelta(hours=1, minutes=25),
            'is_recurring': True,
            'timezone': 'UTC',
            'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
          }
        ),
        TimerPayload.model_validate(
          {
            'label': '25-minute timer',
            'duration': 'PT25M',
            'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
          }
        ),
      ],
    ),
  ) -> ScheduleRecord:
    """
    Create a new scheduled event such as an alarm or timer.

    This endpoint accepts structured input to register a scheduled action
    that will be triggered at a specific time or after a defined duration.
    Supported types include alarms, timers, and other time-based events.

    The request body must include all necessary fields depending on the
    schedule type. Tags are required and must identify the schedule's
    context, such as a user or device, using the format `user:<uuid>` or
    `device:<uuid>`. These tags will later enable filtering and management
    of the scheduled items.

    Once created, the schedule is stored in memory and registered with the
    internal scheduler for future execution.
    """
    return await controller.create_schedule(schedule)

  @api.put(
    '/schedules/{schedule_id}',
    tags=[tag],
    response_model=BaseSchedulePayload,
    responses={
      200: {
        'content': {
          'application/json': {
            # 'example': ScheduleRecord.model_validate(
            #   {
            #     'label': 'Drink water',
            #     'timezone': 'UTC',
            #     'is_recurring': True,
            #     'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
            #   }
            # ),
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
  async def update_schedule(
    schedule_id: UUID = Path(
      ..., description='ID of the schedule to update', examples=['123e4567-e89b-12d3-a456-426614174000']
    ),
    payload: SchedulePayload = Body(
      ...,
      description='Details of the schedule to update.',
      examples=[
        ReminderPayload.model_validate(
          {
            'type': 'reminder',
            'label': 'Drink water',
            'time': datetime.now() + timedelta(hours=1, minutes=25),
            'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
          }
        ),
      ],
    ),
  ) -> Schedule:
    """
    Update an existing schedule by ID with new information.

    This endpoint allows clients to update an existing schedule's properties,
    such as its label, type, scheduled time, and associated tags. It is
    intended for clients who need to revise the details of a previously
    created schedule, without the need to cancel or recreate it.

    When invoked, the endpoint looks up the schedule by its unique identifier.
    If found, it applies the updates from the request payload. If the schedule
    does not exist, a 404 error is returned. The schedule's time must be
    timezone-aware and scheduled in the future. The update preserves the
    schedule's ID while allowing updates to mutable fields.

    This is useful for updating timers, reminders, or any scheduled task,
    particularly when triggered by a user or system change.
    """
    updated = await controller.update_schedule(schedule_id, payload)

    if not updated:
      raise HTTPException(status_code=404, detail='Schedule not found')

    return updated

  @api.get(
    '/schedules',
    tags=[tag],
    responses={
      200: {
        'content': {
          'application/json': {
            'example': [
              ScheduleRecord.model_validate(
                {
                  'id': '123e4567-e89b-12d3-a456-426614174000',
                  'type': 'alarm',
                  'scheduled_time': '2025-12-01T10:00:00Z',
                  'label': 'Meeting reminder',
                  'status': 'scheduled',
                  'tags': ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
                },
              ),
            ],
          },
        },
      },
    },
  )
  async def list_schedules(
    tags: list[str] = Query(
      ...,
      min_length=1,
      description='Optional tag filters (e.g., "user:<uuid>", "device:<uuid>"). Returns schedules matching any of the given tags.',
      examples=[
        ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c'],
        ['device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
        ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
      ],
    ),
    type_filter: ScheduleType | None = Query(
      None,
      alias='type',
      description='Filter schedules by type.',
      examples=[
        'alarm',
        'timer',
        'reminder',
      ],
    ),
  ) -> list[ScheduleRecord]:
    """
    Retrieve all schedules matching provided tags and type filters.

    This endpoint returns a list of scheduled items such as alarms, timers, or
    reminders filtered by specified tags and schedule type. It allows clients
    to obtain schedules related to particular users or devices by filtering on
    tags like "user:<uuid>" or "device:<uuid>", and to further narrow results
    based on the schedule type (e.g., alarm or timer).

    The schedules returned are those that match at least one of the given tags
    and the optional type filter. Results are sorted chronologically by their
    scheduled time to facilitate display of upcoming events in client
    applications.
    """
    # schedules = await controller.get_schedule_records(tags, type_filter)
    schedules = await controller.get_due_schedules(datetime.now())

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
  ) -> GenericResponse:
    """
    Cancel a scheduled alarm, timer, or reminder by ID.

    This endpoint deletes a previously scheduled event identified by its
    unique ID. If the event exists in the system and has not yet executed,
    it will be removed from the scheduler and no further actions will be
    taken on it.

    If the specified schedule ID does not correspond to any active schedule,
    the server responds with a 404 error indicating that the schedule was not
    found. This operation is useful when users change their plans or want to
    revoke a scheduled action before it triggers.
    """
    await controller.delete_schedule(schedule_id)

    return GenericResponse(ok=True)

  async def event_generator(queue: ScheduleQueue) -> AsyncGenerator[str, None]:
    try:
      while True:
        payload = await queue.get()
        data = payload.model_dump_json()

        yield f'data: {data}\n\n'
    except asyncio.CancelledError:
      pass

  @api.get('/schedules/events', tags=[tag], response_model=ScheduleRecord)
  async def stream_schedule_events(
    request: Request,
    tags: list[str] = Query(
      ...,
      min_length=1,
      description=(
        'Optional tag filters (e.g., "user:<uuid>", "device:<uuid>"). Streams events matching any of the given tags.'
      ),
      examples=[
        ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c'],
        ['device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
        ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
      ],
    ),
  ) -> StreamingResponse:
    """
    Establishes a real-time Server-Sent Events (SSE) stream for schedule updates.

    This endpoint provides a persistent SSE connection that delivers real-time
    updates to clients as new schedule events occur. Clients must supply one or
    more tags, such as user or device identifiers, to receive events that match
    any of the specified filters.

    Once connected, the client is registered as a subscriber to receive relevant
    notifications. Events are streamed as they become available, enabling
    low-latency communication ideal for alarms, reminders, and timers. If the
    client disconnects, the server automatically unregisters the subscriber and
    cleans up resources.

    This mechanism is particularly useful for applications that need instant
    updates without polling. It ensures clients stay synchronized with the
    latest scheduled events while conserving backend and network resources.

    **Usage example (JavaScript):**

    ```javascript
    const eventSource = new EventSource('/api/schedules/events?tags=user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c');

    eventSource.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);

        console.log('New schedule event:', data);
        // Process the parsed schedule event
      } catch (error) {
        console.error('Failed to parse event data:', error);
      }
    });

    eventSource.addEventListener('error', (error) => {
      console.error('EventSource failed:', error);
      eventSource.close();
    });

    // To close the connection when no longer needed:
    // eventSource.close();
    ```
    """
    queue: ScheduleQueue = asyncio.Queue()

    await controller.register_subscriber(tags, queue)
    await controller.start_watcher()

    async def event_stream():
      try:
        async for event in event_generator(queue):
          yield event

          if await request.is_disconnected():
            break
      finally:
        await controller.unregister_subscriber(tags, queue)

    return StreamingResponse(event_stream(), media_type='text/event-stream')
