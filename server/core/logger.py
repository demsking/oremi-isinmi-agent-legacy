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
import logging

from oremi_core.logger import Logger

from .config import LOG_FILE
from .config import LOG_LEVEL
from .package import APP_NAME

# Map log level strings to their corresponding integer values
LOG_LEVEL_MAP = {
  'DEBUG': logging.DEBUG,
  'INFO': logging.INFO,
  'WARNING': logging.WARNING,
  'ERROR': logging.ERROR,
  'CRITICAL': logging.CRITICAL,
}


def create_logger(suffix: str = '') -> logging.Logger:
  """
  Create a logger with the specified name and the global log level.
  """
  log_level = LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO)  # Default to INFO if invalid
  name = f'{APP_NAME} - {suffix}' if suffix else APP_NAME

  # Set global log level and create logger
  Logger.set_global_level(log_level)  # type: ignore

  return Logger.create(name, filename=LOG_FILE, level=log_level)


def is_debug() -> bool:
  """
  Check if the current log level is DEBUG.
  """
  return LOG_LEVEL == 'DEBUG'
