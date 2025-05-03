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
import argparse
import json
from typing import Any

import faiss
import numpy as np

from server.core.engine import Engine
from server.core.logger import create_logger

parser = argparse.ArgumentParser(description=' Build Index Script')
parser.add_argument('--language', type=str, required=True)

args = parser.parse_args()
language = args.language

logger = create_logger(language)
engine = Engine(language, logger)

engine.load_model()

# Load dataset
logger.info(f'Loading dataset {engine.data_file}')
with engine.data_file.open('r', encoding='utf-8') as file:
  entries: list[dict[str, Any]] = [json.loads(line) for line in file.readlines() if line.strip()]

# Encode and normalize input sentences
logger.info(f'Encoding {len(entries)} entries')
sentences = [e['input'] for e in entries]
embeddings = engine.model.encode(sentences, normalize_embeddings=True)
embeddings = np.array(embeddings).astype('float32')
faiss.normalize_L2(embeddings)

# Create FAISS index with inner product
logger.info('Creating FAISS index')
index = faiss.IndexFlatIP(embeddings.shape[1])

# pylint: disable=no-value-for-parameter
index.add(embeddings)
# pylint: enable=no-value-for-parameter

# Save the FAISS index to disk
logger.info(f'Writing index to {engine.index_file}')
engine.index_file.parent.mkdir(exist_ok=True)
faiss.write_index(index, str(engine.index_file))
