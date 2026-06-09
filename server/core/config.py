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
import os
import multiprocessing

from oremi_core.vars import getenv

from .package import APP_NAME

HOST: str = getenv('HOST', default='127.0.0.1')
"""
Host address to listen on.
"""

PORT: int = getenv('PORT', default=7337, expected_type=int)
"""
Port number to listen on.
"""

OLLAMA_BASEURL: str = getenv('OLLAMA_BASEURL')
"""
Base URL of the Ollama API.
Required for communication with Ollama services.
"""

OLLAMA_MODEL: str = getenv('OLLAMA_MODEL', default='qwen2.5:3b')
"""
Model name to use for Ollama services.
"""

CACHE_DIR = getenv('CACHE_DIR', default=os.path.expanduser(f'~/.cache/{APP_NAME}'))
"""The directory in which to store cached data."""

ROOT_PATH: str = getenv('ROOT_PATH', default='/')
"""The root path for the API, which defines the base URL path for all routes."""

LOG_FILE: str = getenv('LOG_FILE', default='')
"""Path to the log file where application logs will be stored. If left empty, logs may be directed
to the console by default."""

LOG_LEVEL: str = getenv('LOG_LEVEL', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
"""The log level used to control the verbosity of application logs."""

STORE_URL: str = getenv('STORE_URL', default='sqlite+aiosqlite:///store.sqlite')
"""The connection URL for the SQLAlchemy store."""

TIMEZONE: str = getenv('TZ', default='UTC')
"""
The timezone used for scheduling tasks (e.g., 'UTC', 'Africa/Douala').
"""

EXECUTOR_THREADPOOL_SIZE: int = getenv('EXECUTOR_THREADPOOL_SIZE', default=multiprocessing.cpu_count(), expected_type=int)
"""
Maximum number of threads used by the default ThreadPoolExecutor.
"""

EXECUTOR_PROCESSPOOL_SIZE: int = getenv('EXECUTOR_PROCESSPOOL_SIZE', default=5, expected_type=int)
"""
Maximum number of processes used by the ProcessPoolExecutor.
"""

JOB_COALESCE: bool = getenv('JOB_COALESCE', default=False, expected_type=bool)
"""
Whether to coalesce missed job runs into one.
"""

JOB_MAX_INSTANCES: int = getenv('JOB_MAX_INSTANCES', default=3, expected_type=int)
"""
Maximum number of concurrently running instances allowed for the same job.
"""
