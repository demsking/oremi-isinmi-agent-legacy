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
from enum import Enum
from typing import Any
from typing import Literal

import isodate
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer
from pydantic import field_validator

from .time import get_current_datetime


class GenericResponse(BaseModel):
  ok: bool


class NaturalLanguageRequest(BaseModel):
  text: str = Field(
    ...,
    description='A natural language description of the schedule.',
    examples=[
      'Set a reminder for a meeting at 10 AM tomorrow.',
      'Programme une alarme pour une réunion à 10h du mardi prochain.',
      'Set a timer for 25 minutes.',
    ],
  )

  webhook_url: str = Field(
    ...,
    description='The URL to call when the schedule triggers.',
    examples=[
      'https://example.com/webhook',
      'https://webhook.site/unique-id',
    ],
  )

  webhook_payload: dict | None = Field(
    None,
    description='Optional payload to include in the webhook call.',
    examples=[
      {'key': 'value'},
      {'event': 'meeting', 'priority': 'high'},
    ],
  )

  timezone: str = Field(
    default='UTC',
    description='The timezone in which the schedule should occur.',
    examples=['Europe/Paris', 'Africa/Douala', 'Africa/Lagos', 'America/New_York', 'Asia/Tokyo'],
  )

  context: str | None = Field(
    default=None,
    description='Additional context information for the schedule.',
    examples=['Meeting with John at 10 AM tomorrow', 'Reminder for a meeting'],
  )

  @property
  def current_datetime(self) -> str:
    return get_current_datetime(self.timezone).strftime('%A, %B %d, %Y %I:%M:%S %p')

  def __str__(self) -> str:
    return f'User Request: {self.text}.\nCurrent Date Time: {self.current_datetime}.\n{self.context or ""}'


class ScheduleType(str, Enum):
  ALARM = 'alarm'
  TIMER = 'timer'
  REMINDER = 'reminder'


class BaseScheduleRequest(BaseModel):
  label: str = Field(..., description='The label of the schedule.')
  webhook_url: str = Field(..., description='The URL to call when the schedule triggers.')
  webhook_payload: dict | None = Field(None, description='Optional payload to include in the webhook call.')
  timezone: str = Field('UTC', description='The timezone for the schedule, in IANA format.')
  is_recurring: bool = Field(False, description='Whether the alarm should repeat daily')

  @field_validator('webhook_url')
  @classmethod
  def validate_webhook_url(cls, value: str) -> str:
    if not (value.startswith('http://') or value.startswith('https://')):
      raise ValueError('Webhook URL must start with http:// or https://')

    return value


class AlarmPayload(BaseScheduleRequest):
  type: Literal['alarm'] = 'alarm'
  time: datetime = Field(..., description='When the alarm should trigger', examples=['2025-04-10T15:42:04.175Z'])

  @field_validator('time')
  @classmethod
  def validate_future_time(cls, value: datetime) -> datetime:
    if value < datetime.now(tz=value.tzinfo):
      raise ValueError('Schedule time must be in the future')

    return value

  @field_serializer('time', when_used='unless-none')
  def serialize_time(self, time: datetime):
    return time.isoformat()


class TimerPayload(BaseScheduleRequest):
  type: Literal['timer'] = 'timer'
  duration: timedelta = Field(
    ..., description='Duration for timers in ISO 8601 format (e.g., PT1H30M).', examples=['PT1H30M', 'PT24H']
  )

  @field_validator('duration', mode='before')
  @classmethod
  def validate_duration(cls, value: Any) -> timedelta | None:
    if value is None:
      return None

    if isinstance(value, str):
      try:
        # Parse ISO 8601 duration string (e.g., PT1H30M)
        return isodate.parse_duration(value)
      except ValueError as error:
        raise ValueError('Duration must be in ISO 8601 format (e.g., PT1H30M)') from error

    return value


class ReminderPayload(BaseScheduleRequest):
  """Request model for reminder scheduling"""

  type: Literal['reminder'] = 'reminder'
  time: datetime = Field(..., description='When the reminder should trigger', examples=['2025-04-10T15:42:04.175Z'])

  @field_validator('time')
  @classmethod
  def validate_future_time(cls, value: datetime) -> datetime:
    if value < datetime.now(tz=value.tzinfo):
      raise ValueError('Schedule time must be in the future')

    return value

  @field_serializer('time', when_used='unless-none')
  def serialize_time(self, time: datetime):
    return time.isoformat()


ScheduleRequest = AlarmPayload | TimerPayload | ReminderPayload


class ScheduleRecord(BaseModel):
  id: str = Field(..., description='The unique ID of the schedule.')
  type: ScheduleType = Field(..., description='The type of schedule (e.g., alarm, timer, reminder).')
  label: str = Field(..., description='The label of the schedule.')
  scheduled_time: datetime = Field(..., description='The scheduled time in ISO 8601 format.')
  webhook_url: str = Field(..., description='The URL to call when the schedule triggers.')
  status: str = Field('scheduled', description='The current status of the schedule (e.g., scheduled, triggered).')

  @field_serializer('scheduled_time', when_used='unless-none')
  def serialize_scheduled_time(self, time: datetime):
    return time.isoformat()


class WebhookResponse(BaseModel):
  success: bool = Field(..., description='Indicates if the webhook call was successful.')
  message: str = Field(..., description='A message describing the result of the webhook call.')
  status_code: int = Field(..., description='The HTTP status code returned by the webhook call.')
