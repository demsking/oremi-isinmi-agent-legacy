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
from datetime import timezone
from uuid import uuid4

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String

from .database import Base
from .database import GUID
from .models import ScheduleType


class Schedule(Base):
  __tablename__ = 'schedules'

  id = Column(GUID(), primary_key=True, default=uuid4, unique=True, nullable=False)
  type = Column(SQLEnum(ScheduleType), nullable=False)
  label = Column(String, nullable=False)
  timezone = Column(String, nullable=False)
  is_recurring = Column(Boolean, default=False, nullable=False)
  scheduled_time = Column(DateTime(timezone=True), nullable=True)  # For alarms & reminders
  duration_seconds = Column(Integer, nullable=True)  # For timers
  tags = Column(JSON, nullable=False)
  created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
  updated_at = Column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc),
    onupdate=lambda: datetime.now(timezone.utc),
  )
