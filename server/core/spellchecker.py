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

from langid import classify
from symspellpy import SymSpell
from symspellpy import Verbosity

# Dictionaries can be found at:
# https://github.com/wolfgarbe/SymSpell/tree/master/SymSpell.FrequencyDictionary


class SpellChecker:
  def __init__(self, lang: str, *, dictionary_path: str, logger: logging.Logger) -> None:
    self.sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
    self.lang = lang
    self.logger = logger
    self.dictionary_path = dictionary_path

  def load_dictionaries(self) -> None:
    self.logger.info(f'Loading dictionary for {self.lang}...')
    self.sym_spell.load_dictionary(self.dictionary_path, term_index=0, count_index=1)

  @staticmethod
  def detect_language(text: str) -> tuple[str, float]:
    """
    Detect the language of the input text.
    :param text: The input text to detect language.
    :return: Language code (e.g., 'en' for English, 'fr' for French, etc.)
    """
    return classify(text)

  def fix_word(self, word: str) -> str:
    # Use the appropriate dictionary based on the detected language
    suggestions = self.sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)

    return suggestions[0].term if suggestions else word

  def fix_sentence(self, sentence: str) -> str:
    words = sentence.split()
    corrected_words = []

    for word in words:
      # Detect the language of the word (can be optimized, here we detect for each word)
      corrected_word = self.fix_word(word)
      corrected_words.append(corrected_word)

    # Join the corrected words into a sentence
    return ' '.join(corrected_words)
