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
import json
import logging
from typing import Any
from typing import ClassVar
from typing import Literal

import faiss
import numpy as np
from oremi_core.event import Event
from sentence_transformers import SentenceTransformer

from .package import PROJECT_DIRECTORY
from .spellchecker import SpellChecker

SupportedLanguage = Literal['fr', 'en']


class Engine:
  MODEL_PATH = PROJECT_DIRECTORY / 'models'
  SYMSPELL_MODELS_PATH = MODEL_PATH / 'symspell'
  PODCAST_MODELS = MODEL_PATH / 'isinmi'

  model: SentenceTransformer
  index: Any
  outputs: list[dict]

  dictionaries: ClassVar[dict[SupportedLanguage, str]] = {
    'fr': str(SYMSPELL_MODELS_PATH / 'fr-100k.txt'),
    'en': str(SYMSPELL_MODELS_PATH / 'en-80k.txt'),
  }

  models: ClassVar[dict[SupportedLanguage, str]] = {
    'fr': 'dangvantuan/sentence-camembert-base',
    'en': 'all-MiniLM-L12-v2',
  }

  def __init__(self, language: SupportedLanguage, logger: logging.Logger) -> None:
    self.ready = Event()
    self.loading = False
    self.logger = logger
    self.language: SupportedLanguage = language
    self.index_file = Engine.PODCAST_MODELS / f'{language}-index.faiss'
    self.data_file = Engine.PODCAST_MODELS / f'{language}-data.jsonl'
    self.spellchecker = SpellChecker(
      lang=language,
      dictionary_path=Engine.dictionaries[language],
      logger=logger,
    )

  def get_model(self) -> SentenceTransformer:
    model_name = Engine.models[self.language]

    self.logger.info(f'Loading model {model_name}...')
    return SentenceTransformer(model_name)

  async def load(self) -> None:
    if not self.ready.is_set() and not self.loading:
      self.loading = True

      self.load_model()
      self.load_index()
      self.spellchecker.load_dictionaries()
      self.ready.set()
    else:
      await self.ready.wait()

  def load_model(self) -> None:
    self.model = self.get_model()

  def load_index(self) -> None:
    # Load FAISS index
    self.logger.info(f'Loading index {self.index_file}...')
    self.index = faiss.read_index(str(self.index_file))

    # Verify index dimensions
    self.logger.debug(f'Index dimension: {self.index.d}')

    # Load examples
    self.logger.info(f'Loading examples {self.data_file}...')
    with self.data_file.open('r', encoding='utf-8') as file:
      self.outputs = [json.loads(line) for line in file.readlines() if line.strip()]

  def find_similar(self, query: str) -> tuple[float, dict]:
    # Encode and normalize query
    query_embedding = self.model.encode(query, normalize_embeddings=True)
    query_embedding = np.array(query_embedding).astype('float32').reshape(1, -1)  # Ensure 2D array
    faiss.normalize_L2(query_embedding)

    # Verify embedding dimensions match index
    assert query_embedding.shape[1] == self.index.d, f'Embedding dim {query_embedding.shape[1]} != index dim {self.index.d}'

    # Search top 5 in FAISS index
    D, I = self.index.search(query_embedding, k=1)  # noqa: E741
    idx, score = I[0][0], D[0][0]

    retrieved = score, self.outputs[idx]

    return score, retrieved[1]

  def predict(self, query: str) -> tuple[float, dict]:
    q = self.spellchecker.fix_sentence(query)
    score, retrieved = self.find_similar(q)

    self.logger.debug(f'Retrieved example with score {score:.4f}: {retrieved}')

    return score, retrieved

  class UnknowServiceError(ValueError):
    ...

  class MissingParameterError(ValueError):
    def __init__(self, message: str) -> None:
      self.message = message
