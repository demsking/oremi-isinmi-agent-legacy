APP_NAME := $(shell python scripts/metadata.py name)
APP_VERSION := $(shell python scripts/metadata.py version)
IMAGE_NAME := demsking/$(APP_NAME)

COMPOSE_SERVICES := ollama

# Start the development environment using tmuxinator
shell:
	tmuxinator

stop:
	tmux kill-session -t oremi-isinmi-agent

up: pull
	docker compose -f .devcontainer/workspace.yaml up -d $(COMPOSE_SERVICES) --remove-orphans

.PHONY: config
config:
	docker compose -f .devcontainer/workspace.yaml config

logs:
	docker compose -f .devcontainer/workspace.yaml logs -f

pull:
	docker compose -f .devcontainer/workspace.yaml pull $(COMPOSE_SERVICES)

restart:
	docker compose -f .devcontainer/workspace.yaml restart $(COMPOSE_SERVICES)

down:
	docker compose -f .devcontainer/workspace.yaml down $(COMPOSE_SERVICES)

stats:
	docker compose -f .devcontainer/workspace.yaml stats

gen-tests:
	python scripts/generate-tests.py

test:
	uv run pytest -vv

coverage:
	uv run pytest --cov=server

coverage-html:
	uv run pytest --cov=server --cov-report=html

lint:
	pre-commit run --all-files

fix:
	ruff check . --fix

#
## Dependencies
install:
	rm -rf .venv
	uv venv
	uv sync

outdated:
	uv pip list --outdated

update:
	uv sync --upgrade
	devbox update
	pre-commit autoupdate


#
## Dictionaries

# Dictionaries can be found at:
# https://github.com/wolfgarbe/SymSpell/tree/master/SymSpell.FrequencyDictionary
LANGUAGES := en fr
MODELS_DIR := models/symspell
DICTIONARY_URLS := https://raw.githubusercontent.com/wolfgarbe/SymSpell/refs/heads/master/SymSpell.FrequencyDictionary

# Define the file names for downloaded dictionaries with language codes
DICTIONARY_FILES := en-80k.txt fr-100k.txt
DICTIONARY_MODELS := $(addprefix $(MODELS_DIR)/, $(DICTIONARY_FILES))

# Default target: download all dictionaries
symspell-models: $(DICTIONARY_MODELS)

# Rule to download each dictionary and rename it with the language code
$(DICTIONARY_MODELS):
	mkdir -p $(MODELS_DIR)
	echo "Downloading and renaming dictionary for $@..." && \
	curl -o $@ $(DICTIONARY_URLS)/$(notdir $@)

# Clean target to remove downloaded dictionaries
clean-dictionaries:
	@echo "Cleaning up..."
	@rm -f $(MODELS_DIR)


#
## Index
models/isinmi/en-index.faiss:
	python scripts/build-index.py --language en

models/isinmi/fr-index.faiss:
	python scripts/build-index.py --language fr

index: models/isinmi/fr-index.faiss models/isinmi/en-index.faiss

clean-index:
	rm -rf models/isinmi/

resources: symspell-models index
clean: clean-dictionaries clean-index


#
## Documentation
.PHONY: doc/openapi.json
doc/openapi.json:
	python scripts/generate-openapi.py > $@

#
## Packaging
image: resources
	@echo "Building $(IMAGE_NAME):$(APP_VERSION)"
	uv lock
	docker build . \
	  --progress plain \
	  --tag $(IMAGE_NAME):$(APP_VERSION) \
	  --tag $(IMAGE_NAME):latest \
	  --label "org.opencontainers.image.title=$(APP_NAME)" \
	  --label "org.opencontainers.image.description=$(shell python scripts/metadata.py description)" \
	  --label "org.opencontainers.image.version=$(APP_VERSION)" \
	  --label "org.opencontainers.image.revision=$(shell git rev-parse HEAD)" \
	  --label "org.opencontainers.image.authors=Sébastien Demanou <demsking@gmail.com>" \
	  --label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds)" \
	  --label "org.opencontainers.image.vendor=Sébastien Demanou" \
	  --label "org.opencontainers.image.licenses=$(shell python scripts/metadata.py license)"

image-test: resources
	uv lock
	docker build . \
	  --progress plain \
	  --tag $(IMAGE_NAME):test

publish: image
	git commit pyproject.toml uv.lock -m "Release $(APP_VERSION)"
	docker push $(IMAGE_NAME):$(APP_VERSION)
	docker push $(IMAGE_NAME):latest
	git tag v$(APP_VERSION)
	git push --tags origin main
