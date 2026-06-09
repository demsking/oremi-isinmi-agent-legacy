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
import shutil
from pathlib import Path
from typing import Any
from typing import ClassVar
from typing import Literal

import faiss
import numpy as np
from oremi_core.event import Event
from sentence_transformers import SentenceTransformer

from .config import CACHE_DIR
from .package import PROJECT_DIRECTORY
from .spellchecker import SpellChecker

SupportedLanguage = Literal['fr', 'en']


class Engine:
  MODELS_PATH = PROJECT_DIRECTORY / 'models'
  SYMSPELL_MODELS_PATH = MODELS_PATH / 'symspell'
  ENGINE_MODELS_PATH = MODELS_PATH / 'isinmi'

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
    self.index_file = Engine.ENGINE_MODELS_PATH / f'{language}-index.faiss'
    self.data_file = Engine.ENGINE_MODELS_PATH / f'{language}-data.jsonl'
    self.spellchecker = SpellChecker(
      lang=language,
      dictionary_path=Engine.dictionaries[language],
      logger=logger,
    )

  async def load(self) -> None:
    if not self.ready.is_set() and not self.loading:
      self.loading = True
      try:
        self.load_model()
        self.load_index()
        self.spellchecker.load_dictionaries()
        self.ready.set()
      finally:
        # Always release the loading guard so a failed load can be retried.
        self.loading = False
    else:
      await self.ready.wait()

  @staticmethod
  def get_cache_folder() -> Path:
    cache_dir = Path(CACHE_DIR) / 'sentence-transformers'
    cache_dir.mkdir(parents=True, exist_ok=True)

    return cache_dir

  @staticmethod
  def get_cached_model_dir(cache_folder: Path, model_name: str) -> Path:
    return cache_folder / f'models--{model_name.replace("/", "--")}'

  def load_model(self) -> None:
    model_name = Engine.models[self.language]
    cache_folder = Engine.get_cache_folder()

    self.logger.info(f'Loading model {model_name} from cache {cache_folder}...')

    try:
      self.model = SentenceTransformer(model_name, cache_folder=str(cache_folder))
    except Exception as error:
      if 'InvalidHeaderDeserialization' not in str(error):
        raise

      corrupted_cache = Engine.get_cached_model_dir(cache_folder, model_name)
      self.logger.warning(f'Corrupted model cache detected at {corrupted_cache}; forcing a clean redownload.')
      shutil.rmtree(corrupted_cache, ignore_errors=True)
      self.model = SentenceTransformer(
        model_name,
        cache_folder=str(cache_folder),
        model_kwargs={
          'force_download': True,
        },
      )

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

    self.logger.debug(f'Retrieved example with score {score:.4f} for input "{q}": {retrieved}')

    return score, retrieved

  class UnknowServiceError(ValueError):
    ...

  class MissingParameterError(ValueError):
    def __init__(self, message: str) -> None:
      self.message = message
