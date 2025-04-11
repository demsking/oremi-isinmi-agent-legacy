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
import multiprocessing
import os

from oremi_core.vars import getenv

from .package import APP_NAME
from .package import APP_VERSION

HOST = getenv('HOST', default='127.0.0.1')
"""
Host address to listen on.
"""

PORT = getenv('PORT', default=7337, expected_type=int)
"""
Port number to listen on.
"""

OLLAMA_BASEURL = getenv('OLLAMA_BASEURL')
"""
Base URL of the Ollama API.
Required for communication with Ollama services.
"""

OLLAMA_MODEL = getenv('OLLAMA_MODEL', default='llama3.2')
"""
Model name to use for Ollama services.
"""

USER_AGENT = getenv('USER_AGENT', default=f'{APP_NAME}/{APP_VERSION}')
"""
User agent string for HTTP requests.

This string identifies the application and its version in HTTP requests.
"""

CACHE_DIR = getenv('CACHE_DIR', default=os.path.expanduser(f'~/.cache/{APP_NAME}'))
"""The directory in which to store cached data."""

ROOT_PATH = getenv('ROOT_PATH', default='/')
"""The root path for the API, which defines the base URL path for all routes."""

LOG_FILE = getenv('LOG_FILE', default='')
"""Path to the log file where application logs will be stored. If left empty, logs may be directed
to the console by default."""

LOG_LEVEL = getenv('LOG_LEVEL', default='INFO')
"""The log level used to control the verbosity of application logs. Options include 'DEBUG', 'INFO',
'WARNING', 'ERROR', and 'CRITICAL'."""

WORKERS = getenv('WORKERS', default=multiprocessing.cpu_count(), expected_type=int)
"""The number of worker processes to run for handling incoming API requests. By default, it uses
the number of CPU cores available on the system."""
