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
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import CHAR
from sqlalchemy.types import TypeDecorator

from .config import STORE_URL
from .logger import is_debug


class GUID(TypeDecorator):
  impl = CHAR

  def load_dialect_impl(self, dialect):
    if dialect.name == 'postgresql':
      from sqlalchemy.dialects.postgresql import UUID as PGUUID

      return dialect.type_descriptor(PGUUID(as_uuid=True))
    else:
      return dialect.type_descriptor(CHAR(36))

  def process_bind_param(self, value, dialect):
    if value is None:
      return value
    if not isinstance(value, uuid.UUID):
      return str(uuid.UUID(value))
    return str(value)

  def process_result_value(self, value, dialect):
    if value is None:
      return value
    return uuid.UUID(value)


engine = create_async_engine(STORE_URL, echo=is_debug(), future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


async def initialize_database() -> None:
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
