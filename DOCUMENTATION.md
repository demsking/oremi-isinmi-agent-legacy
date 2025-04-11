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
- Natural language understanding via Ollama (LLaMA3.2)
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

### Deploy with Docker

Use the official Docker image [`demsking/oremi-isinmi-agent`](https://hub.docker.com/r/demsking/oremi-isinmi-agent)
to run Oremi Isinmi Agent:

```sh
docker run -d --env-file <path_to_env_file> -p 7337:7337 demsking/oremi-isinmi-agent
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
    volumes:
      - ~/.config/oremi-isinmi-agent:/var/cache/oremi-isinmi-agent
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

### HTTP Configuration

- **HOST**: The host address on which the application will listen. Default is `"127.0.0.1"`.
- **PORT**: The port number on which the application will listen. Default is `7337`.
- **USER_AGENT**: User agent string for HTTP requests. This string identifies
  the application and its version in HTTP requests. Default is
  `"<APP_NAME>/<APP_VERSION>"`.

### Caching Configuration

These variables control HTTP request behavior and caching settings.

- **CACHE_DIR**:
  The directory in which to store cached data. Defaults to `'/usr/local/cache'`.

### Ollama Configuration

- **OLLAMA_BASEURL**: Base URL of the Ollama API. Required for communication with Ollama services.
- **OLLAMA_MODEL**: Model name to use for Ollama services. Default is `"llama3.2"`.

### API and Logging Configuration

These variables control the API root path, logging behavior, and server settings.

- **ROOT_PATH**:
  Defines the base URL path for all API routes. Defaults to `'/'`.

- **LOG_FILE**:
  Path to the log file for storing application logs. Empty defaults to console.

- **LOG_LEVEL**:
  Controls the verbosity of logs. Options: `'DEBUG'`, `'INFO'`, `'WARNING'`,
  `'ERROR'`, `'CRITICAL'`. Defaults to `'INFO'`.

### Performance Configuration

Settings that control the server's performance.

- **WORKERS**:
  The number of worker processes for handling requests. Defaults to the
  number of CPU cores on the system.
