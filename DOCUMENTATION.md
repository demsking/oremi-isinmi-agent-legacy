**Oremi Isinmi Agent** is a powerful and user-friendly API for retrieving weather
forecasts, air quality data, pollen levels, geographical location data, and
server-related information. Built with FastAPI and designed to run in a Docker
container, Oremi Isinmi Agent provides developers with easy access to accurate
weather and geocoding data.

![Oremi Isinmi Agent Logo](logo.jpg)

## Features

- Alarm scheduling with custom labels and recurrence
- Flexible timers with countdown and cancellation support
- Persistent reminders with optional recurrence
- Calendar event creation and management
- Natural language understanding via Ollama (qwen2.5:3b)
- Built with a focus on performance and security
- Easily deployable using the [`demsking/oremi-isinmi-agent`](https://hub.docker.com/r/demsking/oremi-isinmi-agent)
  Docker image.

## Deployment

### Docker Image

The [`demsking/oremi-isinmi-agent`](https://hub.docker.com/r/demsking/oremi-isinmi-agent)
Docker image is officially available on Docker Hub, supporting both
`linux/amd64` and `linux/arm64` platforms. The image is configured to expose
port `7337`, which serves the API and documentation endpoints.

The local documentation can be accessed at `http://localhost:7337/docs` for easy
reference on available endpoints and usage instructions.

## Volumes

The Oremi Isinmi Agent container uses a volume to persist cached data across
container restarts and updates. This cache typically stores temporary
processing results, model artifacts, or other runtime data that improves
performance and reduces redundant computations.

- **Container path:** `/var/cache/oremi-isinmi-agent`
- **Recommended host path:** `~/.cache/oremi-isinmi-agent`

The volume is optional but recommended. Without it, cached data will be lost
when the container is removed, which may lead to increased processing times and
API latency during subsequent requests.

### Deploy with Docker

Use the official Docker image [`demsking/oremi-isinmi-agent`](https://hub.docker.com/r/demsking/oremi-isinmi-agent)
to run Oremi Isinmi Agent:

```sh
docker run -d \
  --env-file <path_to_env_file> \
  -v ~/.config/oremi-isinmi-agent:/var/cache/oremi-isinmi-agent \
  -p 7337:7337 \
  demsking/oremi-isinmi-agent
```

Replace `<path_to_env_file>` with the path to your
[environment variables](#description/environment-variables) file containing the
necessary configurations.

### Deploy with Docker Compose

Create a `compose.yml` file:

```yaml
services:
  agent:
    image: demsking/oremi-isinmi-agent
    depends_on:
      - ollama
    ports:
      - 7337:7337
    volumes:
      - ~/.config/oremi-isinmi-agent:/var/config/oremi-isinmi-agent
    environment:
      OLLAMA_BASEURL: http://ollama:11434

  ollama:
    image: ollama/ollama
    restart: always
    runtime: nvidia
    volumes:
      - ~/.ollama:/root/.ollama
```

Run the container using `docker compose`:

```sh
docker compose up -d
```

## Environment Variables

When configuring **Oremi Isinmi Agent**, several environment variables are used to
control its behavior and connect with external services. Below is a breakdown
of these variables, grouped by their purpose.

### Task Scheduling Configuration

**Oremi Isinmi Agent** supports task scheduling for features such as alarms,
reminders, and timers. The following environment variables allow you to
configure how scheduled tasks are stored, executed, and managed:

- **STORE_URL**: The connection URL for the storage backend used to persist
  scheduled tasks. Default is `"sqlite+aiosqlite:///var/config/oremi-isinmi-agent/store.sqlite"`. For example:
  - `"sqlite+aiosqlite:///var/config/oremi-isinmi-agent/store.sqlite"` for SQLite
  - `"postgresql+psycopg2://user:password@localhost/dbname"` for PostgreSQL
  - `"mysql+pymysql://user:password@localhost/dbname"` for MySQL

- **TIMEZONE**: Timezone used for scheduling tasks. Default is `"UTC"`.
  Use values such as `"Africa/Douala"` or `"Europe/Paris"` depending on your
  region.

- **EXECUTOR_THREADPOOL_SIZE**: Maximum number of threads used by the default
  ThreadPoolExecutor. Defaults to the number of CPU cores available on the
  system (detected via `multiprocessing.cpu_count()`).

- **EXECUTOR_PROCESSPOOL_SIZE**: Maximum number of processes in the
  process pool executor. Default is `5`.

- **JOB_COALESCE**: Whether to coalesce (merge) missed job runs into one
  execution. Default is `false`.

- **JOB_MAX_INSTANCES**: Maximum number of concurrent instances allowed per
  job. Default is `3`.

### HTTP Configuration

- **HOST**: The host address on which the application will listen. Default is `"127.0.0.1"`.
- **PORT**: The port number on which the application will listen. Default is `7337`.

### Ollama Configuration

- **OLLAMA_BASEURL**: Base URL of the Ollama API. Required for communication with Ollama services.
- **OLLAMA_MODEL**: Model name to use for Ollama services. Default is `"qwen2.5:3b"`.

### API and Logging Configuration

These variables control the API root path, logging behavior, and server settings.

- **ROOT_PATH**:
  Defines the base URL path for all API routes. Defaults to `'/'`.

- **LOG_FILE**:
  Path to the log file for storing application logs. Empty defaults to console.

- **LOG_LEVEL**:
  Controls the verbosity of logs. Options: `'DEBUG'`, `'INFO'`, `'WARNING'`,
  `'ERROR'`, `'CRITICAL'`. Defaults to `'INFO'`.

#### How It Works

The scheduler uses the configured `STORE_URL` to persist scheduled jobs,
ensuring tasks survive application restarts. Thread and process pool sizes
control concurrency for running jobs. Timezone ensures correct timing
across regions. Coalescing avoids running missed jobs multiple times if the
scheduler was down. Maximum instances prevent the same job from overlapping
too much.

Defaults provide a balanced configuration but can be adjusted to your
environment and workload.

Example configuration in your `.env` file:

```env
STORE_URL=postgresql+psycopg2://user:pass@localhost/schedule
TIMEZONE=Africa/Douala
EXECUTOR_THREADPOOL_SIZE=10
EXECUTOR_PROCESSPOOL_SIZE=4
JOB_COALESCE=false
JOB_MAX_INSTANCES=3
```

This configuration ensures robust and customizable scheduling for all time-based
features in the Oremi Isinmi Agent.
