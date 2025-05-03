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

import httpx
from ollama import AsyncClient
from ollama import GenerateResponse
from ollama import Options


class Assistant:
  def __init__(
    self,
    *,
    model: str,
    ollama_baseurl: str,
    logger: logging.Logger,
  ) -> None:
    self.logger = logger
    self.model = model
    self.ollama_baseurl = ollama_baseurl
    self.client = AsyncClient(
      host=ollama_baseurl,
      timeout=httpx.Timeout(None),  # no timeout
    )

  def create_agent(self, system: str | None) -> 'Agent':
    return Agent(
      model=self.model,
      ollama_baseurl=str(self.ollama_baseurl),
      logger=self.logger,
      system=system,
    )

  async def load_model(self) -> None:
    self.logger.info(f'Pulling model {self.model}...')
    await self.client.pull(self.model, stream=False)

    self.logger.info(f'Loading model {self.model}...')
    await self.client.generate(
      model=self.model,
      keep_alive=-1,  # any negative number which will keep the model loaded in memory
    )


class Agent:
  def __init__(
    self,
    *,
    model: str,
    ollama_baseurl: str,
    logger: logging.Logger,
    system: str | None = None,
  ) -> None:
    self.logger = logger
    self.model = model
    self.system = system
    self.client = AsyncClient(
      host=ollama_baseurl,
      timeout=httpx.Timeout(None),  # no timeout
    )

  async def generate(
    self,
    prompt: str,
    options: Options | None = None,
  ) -> GenerateResponse:
    """
    Asynchronously generates a response based on the provided prompt and options.

    Args:
      prompt (str): The input prompt to generate a response for.
      options (Options | None, optional): Additional options to customize the generation process. Defaults to None.

    Returns:
      GenerateResponse: The generated response.

    Raises:
      ResponseError: If an error occurs during the generation process.

    Logs:
      - Debug: Logs the prompt being used for generation.
      - Error: Logs any errors encountered during the generation process.
    """
    self.logger.debug(f'Generating with prompt:\n{prompt}')

    return await self.client.generate(
      model=self.model,
      prompt=prompt,
      system=self.system or '',
      stream=False,
      options=options,
    )
