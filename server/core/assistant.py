# Copyright 2025-2026 Sébastien Demanou. All Rights Reserved.
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

import httpx
from ollama import AsyncClient
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider


class Assistant:
  def __init__(
    self,
    *,
    model: str,
    ollama_baseurl: str,
    logger: logging.Logger,
  ) -> None:
    self.logger = logger
    self.model = OpenAIChatModel(
      model_name=model,
      provider=OllamaProvider(
        base_url=f'{ollama_baseurl.rstrip("/")}/v1',
      ),
    )

    self.client = AsyncClient(
      host=ollama_baseurl,
      timeout=httpx.Timeout(None),  # no timeout
    )

  def create_agent(self, system: str | None, output_type: type | None = None) -> 'Agent':
    return Agent(
      model=self.model,
      system_prompt=system,
      output_type=output_type,
      retries=3,
    )

  async def load_model(self) -> None:
    self.logger.info(f'Pulling model {self.model.model_name}...')
    await self.client.pull(self.model.model_name, stream=False)

    self.logger.info(f'Loading model {self.model.model_name}...')
    await self.client.generate(
      model=self.model.model_name,
      keep_alive=-1,  # any negative number which will keep the model loaded in memory
    )
