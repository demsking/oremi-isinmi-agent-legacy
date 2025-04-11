FROM python:3.11-alpine3.21

ENV PATH="/opt/oremi-isinmi-agent/bin:/usr/local/bin:$PATH"
ENV PYTHONPATH="/opt/oremi-isinmi-agent:/usr/local/lib/python3.11/site-packages"
ENV PYTHONUNBUFFERED="1"
ENV PYTHONDONTWRITEBYTECODE="1"

ENV TZ=UTC

ENV HOST="0.0.0.0"
ENV PORT=7337

ENV CACHE_DIR="/var/cache/oremi-isinmi-agent"

ENV OLLAMA_MODEL="demsking/oremi:latest"
ENV OLLAMA_BASEURL=

ENV LOG_LEVEL="info"
ENV LOG_FILE=

# Set the shell to /bin/ash and enable pipefail
SHELL ["/bin/ash", "-eo", "pipefail", "-c"]

# Install dependencies
RUN apk update \
  && apk add --no-cache tzdata

# Upgrade pip and setuptools to the latest version
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Build Python dependencies
COPY build/requirements.txt /opt/oremi-isinmi-agent/
RUN pip install --no-cache-dir -r /opt/oremi-isinmi-agent/requirements.txt

# Binaries
COPY bin/* /opt/oremi-isinmi-agent/bin/
RUN chmod +x /opt/oremi-isinmi-agent/bin/* \
  && mkdir -p /var/cache/oremi-isinmi-agent

# Copy application files
COPY pyproject.toml LICENSE DOCUMENTATION.md /opt/oremi-isinmi-agent/
COPY server/ /opt/oremi-isinmi-agent/server

EXPOSE 7337

CMD ["oremi-isinmi-agent"]
