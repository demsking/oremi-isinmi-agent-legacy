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
from uuid import UUID

import isodate
import pytz
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

  timezone: str = Field(
    default='UTC',
    description='The timezone in which the schedule should occur.',
    examples=['Europe/Paris', 'Africa/Douala', 'Africa/Lagos', 'America/New_York', 'Asia/Tokyo'],
  )

  tags: list[str] = Field(
    ...,
    min_length=1,
    description='Tags used to scope the schedule to a specific user or device.',
    examples=[
      ['user:6e9a9c44-7f55-4b33-8465-9f50d91e6f9a'],
      ['device:7a0c1f5b-2289-4379-8c0e-7617df93f417'],
      ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
    ],
  )

  @property
  def current_datetime(self) -> str:
    return get_current_datetime(self.timezone).strftime('%A, %B %d, %Y %I:%M:%S %p')

  @field_validator('timezone')
  @classmethod
  def validate_timezone(cls, value):
    if value not in pytz.all_timezones:
      raise ValueError('Invalid timezone')
    return value

  def __str__(self) -> str:
    return f'User Request: {self.text}.\nCurrent Date Time: {self.current_datetime}.'


class ScheduleType(str, Enum):
  ALARM = 'alarm'
  TIMER = 'timer'
  REMINDER = 'reminder'


class BaseSchedulePayload(BaseModel):
  label: str = Field(..., description='The label of the schedule.')
  timezone: str = Field('UTC', description='The timezone for the schedule, in IANA format.')
  is_recurring: bool = Field(False, description='Whether the alarm should repeat daily')
  tags: list[str] = Field(
    ...,
    min_length=1,
    description='Tags used to scope the schedule to a specific user or device.',
    examples=[
      ['user:6e9a9c44-7f55-4b33-8465-9f50d91e6f9a'],
      ['device:7a0c1f5b-2289-4379-8c0e-7617df93f417'],
      ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
    ],
  )

  @field_validator('timezone')
  @classmethod
  def validate_timezone(cls, value):
    if value not in pytz.all_timezones:
      raise ValueError('Invalid timezone')
    return value


class AlarmPayload(BaseSchedulePayload):
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


class TimerPayload(BaseSchedulePayload):
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

  @field_serializer('duration', when_used='unless-none')
  @classmethod
  def serialize_duration(cls, duration: timedelta):
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    parts = ['PT']

    if hours:
      parts.append(f'{hours}H')

    if minutes:
      parts.append(f'{minutes}M')

    if seconds or not parts[1:]:
      parts.append(f'{seconds}S')

    return ''.join(parts)


class ReminderPayload(BaseSchedulePayload):
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


SchedulePayload = AlarmPayload | TimerPayload | ReminderPayload


class ScheduleRecord(BaseModel):
  id: UUID = Field(..., description='The unique ID of the schedule.')
  type: ScheduleType = Field(..., description='The type of schedule (e.g., alarm, timer, reminder).')
  label: str = Field(..., description='The label of the schedule.')
  scheduled_time: datetime = Field(..., description='The scheduled time in ISO 8601 format.')
  tags: list[str] = Field(
    ...,
    min_length=1,
    description='Tags used to scope the schedule to a specific user or device.',
    examples=[
      ['user:6e9a9c44-7f55-4b33-8465-9f50d91e6f9a'],
      ['device:7a0c1f5b-2289-4379-8c0e-7617df93f417'],
      ['user:9b172e1e-5218-4c95-a786-2c5a1ffeb09c', 'device:13cbddfc-6e97-4dc4-b44a-184d6deed3e3'],
    ],
  )

  @field_validator('scheduled_time')
  @classmethod
  def ensure_datetime(cls, value: str | datetime) -> datetime:
    if isinstance(value, str):
      return datetime.fromisoformat(value)
    return value

  @field_serializer('scheduled_time', when_used='unless-none')
  def serialize_scheduled_time(self, time: datetime):
    return time.isoformat()
