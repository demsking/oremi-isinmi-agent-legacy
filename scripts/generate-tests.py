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
# pylint: disable=wildcard-import,unused-wildcard-import,invalid-name,line-too-long
import json
import logging
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from slugify import slugify

# Load environment variables from .env file
load_dotenv('.devcontainer/.env')


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


existing_fixtures = ['uid', 'docid']


def starts_with_number(string: str) -> bool:
  return string[0].isdigit()


# Function to load OpenAPI spec from a URL
def load_openapi_spec():
  from server import api

  logging.info('Loading OpenAPI spec')
  client = TestClient(
    api,
    backend='asyncio',
    root_path='',
    follow_redirects=False,
  )

  response = client.get('/openapi.json')
  logging.info('OpenAPI spec loaded successfully')

  return response.json()


# Function to get the existing test files
def get_existing_tests(directory):
  logging.info(f'Checking existing tests in {directory}')
  existing_tests = {}

  for test_file in Path(directory).glob('**/test_*.py'):
    with open(test_file, encoding='utf-8') as f:
      existing_tests[test_file.stem] = f.read()

  logging.info(f'Found {len(existing_tests)} existing test files')
  return existing_tests


# Function to create test file content
def create_test_content(tag, endpoint_name, path, method, details):
  content = """from fastapi.testclient import TestClient

from server import api


client = TestClient(api, backend='asyncio')

"""
  operation_id = details.get('operationId', f'{method}_{path.replace("/", "_")}')
  summary = details.get('summary', operation_id)

  # Handle request body examples
  fixture_names = []

  if method.lower() in ['post', 'put', 'patch']:
    schema = details.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
    example_str = parse_schema_example(schema)

    if example_str:
      fixture_names.append(f'{operation_id}_payload')

  # Handle parameters and query examples
  params = details.get('parameters', [])
  query_params = {}
  path_params_fixtures = []

  for param in params:
    if param['in'] == 'query':
      query_examples = param.get('schema', {}).get('examples', [])

      if query_examples:
        example_value = query_examples[0]
        query_params[param['name']] = example_value
    elif param['in'] == 'path':
      path_examples = param.get('schema', {}).get('examples', [])

      if path_examples:
        example_value = path_examples[0]
        fixture_name = param['name']
        path_params_fixtures.append((param['name'], fixture_name))
        fixture_names.append(fixture_name)

  query_string = f'?{urlencode(query_params)}' if query_params else ''
  formatted_path = path

  for param_name, fixture_name in path_params_fixtures:
    formatted_path = formatted_path.replace(f'{{{param_name}}}', f'{{{fixture_name}}}')

  path_value = f'{formatted_path}{query_string}'
  path_value_prefix = 'f' if '{' in path_value else ''

  if method in ['patch', 'post', 'put']:
    content += f"""
async def test_{operation_id}({', '.join(fixture_names)}):
  \"\"\"{summary}\"\"\"
  path = {path_value_prefix}'{path_value}'
  payload = {fixture_names[0] if fixture_names else '{}'}
  response = client.{method}(path, json=payload)
  assert response.status_code == 200

"""
  else:
    content += f"""
async def test_{operation_id}({', '.join(fixture_names)}):
  \"\"\"{summary}\"\"\"
  path = {path_value_prefix}'{path_value}'
  response = client.{method}(path)
  assert response.status_code == 200

"""

  return content


def add_spaces_to_lines(multiline_string):
  lines = multiline_string.splitlines()
  spaced_lines = ['  ' + line for line in lines]
  return '\n'.join(spaced_lines)


def parse_schema_example(schema):
  examples = schema.get('examples', [])
  example_str = examples[0] if len(examples) > 0 else None
  example_str = json.dumps(example_str, indent=2)
  example_str = example_str.replace('null', 'None')
  example_str = example_str.replace(' false', ' False')
  example_str = example_str.replace(' true', ' True')
  return add_spaces_to_lines(example_str).strip()


def parse_fixture_content(name, content):
  return f"""
@pytest.fixture
def {name}():
  return {content}

"""


def parse_fixture_name(name: str) -> str:
  value = f'_{name}' if starts_with_number(name) else name

  return slugify(value, separator='_')


def create_params_fixtures_content(param):
  fixture_name = param.get('name')
  fixture_name = parse_fixture_name(fixture_name)

  if fixture_name in existing_fixtures:
    return ''

  existing_fixtures.append(fixture_name)

  schema = param.get('schema', {})
  example_str = parse_schema_example(schema)

  return parse_fixture_content(fixture_name, example_str)


# Function to create fixtures file content for POST method payloads and path params
def create_fixtures_content(paths):
  content = (
    '# pylint: disable=wildcard-import,unused-wildcard-import,invalid-name,line-too-long'
    'import pytest\n\n'
    'from dotenv import load_dotenv\n\n'
    '# Load environment variables from .env file\n'
    "load_dotenv('.devcontainer/.env')\n\n"
  )

  for path, methods in paths.items():
    for method, details in methods.items():
      if method.lower() in ['post', 'put', 'patch']:
        operation_id = details.get('operationId', f'{method}_{path.replace("/", "_")}')
        schema = details.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
        example_str = parse_schema_example(schema)

        fixture_name = f'{operation_id}_payload'
        fixture_name = parse_fixture_name(fixture_name)
        content += parse_fixture_content(fixture_name, example_str)

        # Handle path parameter examples
        params = details.get('parameters', [])

        for param in params:
          content += create_params_fixtures_content(param)

  return content


# Function to generate test files
def generate_tests(spec, existing_tests):
  logging.info('Generating test files from OpenAPI spec')
  tag_paths = {}
  servers = spec.get('servers', [])
  path_prefix = servers[0]['url'] if servers else ''

  for path, methods in spec.get('paths', {}).items():
    for method, details in methods.items():
      tags = details.get('tags', ['default'])

      for tag in tags:
        if tag not in tag_paths:
          tag_paths[tag] = {}
        if path not in tag_paths[tag]:
          tag_paths[tag][path] = {}

        tag_paths[tag][path][method] = details

  test_dir = Path('tests')
  test_dir.mkdir(exist_ok=True)

  for tag, paths in tag_paths.items():
    tag_dir = test_dir / tag.replace(' ', '_').lower()
    tag_dir.mkdir(exist_ok=True)

    for path, methods in paths.items():
      for method, details in methods.items():
        endpoint_name = path.strip('/').replace('/', '_')
        test_file_name = f'{method}_{endpoint_name}_test.py'
        test_file_path = tag_dir / test_file_name
        path = path_prefix + path

        if test_file_path.stem not in existing_tests:
          logging.info(f'Creating test file {test_file_path}')
          content = create_test_content(tag, endpoint_name, path, method, details)
          with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
          logging.info(f'Test file {test_file_path} created successfully')
        else:
          logging.info(f'Test file {test_file_path} already exists, skipping')


# Function to generate fixtures file
def generate_fixtures(spec):
  logging.info('Generating fixtures file from OpenAPI spec')
  paths = spec.get('paths', {})
  content = create_fixtures_content(paths)

  fixtures_file_path = Path('tests/conftest.py')
  with open(fixtures_file_path, 'w', encoding='utf-8') as f:
    f.write(content)

  logging.info(f'Fixtures file {fixtures_file_path} created successfully')


# Main script execution
def main():
  spec = load_openapi_spec()
  existing_tests = get_existing_tests('tests')
  generate_tests(spec, existing_tests)
  generate_fixtures(spec)


if __name__ == '__main__':
  main()
