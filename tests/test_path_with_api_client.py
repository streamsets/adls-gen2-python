#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

# Tests for the path related methods of the API Client.

import logging
import string
from uuid import uuid4

import pytest

from downstage.utils import get_random_string

logger = logging.getLogger(__name__)

FEDERER_NAME = 'Roger Federer'
MESSI_NAME = 'Lionel Messi'
RONALDO_NAME = 'Christiano Ronaldo'


@pytest.fixture(scope="module")
def sample_filesystem(adls_gen2_fs_oauth2_api_client):
    filesystem_identifier = get_random_string(string.ascii_lowercase, 6)

    adls_gen2_fs_oauth2_api_client.create_filesystem(filesystem_identifier)
    yield filesystem_identifier

    adls_gen2_fs_oauth2_api_client.delete_filesystem(filesystem_identifier)


@pytest.fixture(scope="module")
def sample_directory(adls_gen2_fs_oauth2_api_client, sample_filesystem):
    directory_name = get_random_string(string.ascii_lowercase, 6)

    kwargs = {'resource': 'directory'}
    headers = {"Content-Length": "0"}
    adls_gen2_fs_oauth2_api_client.create_path(sample_filesystem, directory_name, headers=headers, **kwargs)

    yield directory_name

    adls_gen2_fs_oauth2_api_client.delete_path(sample_filesystem, directory_name)


@pytest.fixture(scope="module")
def sample_file(adls_gen2_fs_oauth2_api_client, sample_filesystem, sample_directory):
    file_name = 'file1.txt'
    path = '{}/{}'.format(sample_directory, file_name)

    kwargs = {'resource': 'file'}
    headers = {'Content-Length': '0', 'x-ms-version': '2018-11-09'}
    adls_gen2_fs_oauth2_api_client.create_path(sample_filesystem, path, headers=headers, **kwargs)
    yield file_name

    adls_gen2_fs_oauth2_api_client.delete_path(sample_filesystem, path)


def test_create_and_delete_directory(adls_gen2_fs_oauth2_api_client, sample_filesystem):
    """Create a filesystem, then a directory under it.
    And verify with list_path call.
    Later delete the directory and verify."""

    directory_name = get_random_string(string.ascii_lowercase, 6)

    kwargs = {'resource': 'directory'}
    headers = {"Content-Length": "0"}
    adls_gen2_fs_oauth2_api_client.create_path(sample_filesystem, directory_name, headers=headers, **kwargs)

    # Verify with list_path.
    list_directory_command = adls_gen2_fs_oauth2_api_client.list_path(sample_filesystem)
    paths = list_directory_command.response.json()['paths']
    assert any([item['name'] for item in paths if item['name'] == directory_name])

    # Delete the directory.
    adls_gen2_fs_oauth2_api_client.delete_path(sample_filesystem, directory_name)

    # Verify with list_path.
    list_directory_command = adls_gen2_fs_oauth2_api_client.list_path(sample_filesystem)
    paths = list_directory_command.response.json()['paths']
    assert not any([item['name'] for item in paths if item['name'] == directory_name])


def test_list_path(adls_gen2_fs_oauth2_api_client, sample_filesystem, sample_directory):
    # List path for the filesystem and verify the directory is listed.
    list_directory_command = adls_gen2_fs_oauth2_api_client.list_path(sample_filesystem)
    paths = list_directory_command.response.json()['paths']
    assert any([item['name'] for item in paths if item['name'] == sample_directory])

    # List path for the directory and verify the contents are empty.
    kwargs = {'directory': sample_directory}
    list_directory_command = adls_gen2_fs_oauth2_api_client.list_path(sample_filesystem, **kwargs)
    paths = list_directory_command.response.json()['paths']
    assert paths == []


def test_lease_path(adls_gen2_fs_oauth2_api_client, sample_filesystem, sample_directory):
    # Test Lease path for the directory.

    # Acquire a lease.
    lease_id = str(uuid4())
    headers = {'x-ms-lease-action': 'acquire',
               'x-ms-proposed-lease-id': lease_id,
               'x-ms-lease-duration': '60',
               'x-ms-version': '2018-11-09'}
    command = adls_gen2_fs_oauth2_api_client.lease_path(sample_filesystem, sample_directory, headers)
    assert command.response.status_code == 201

    # Break the lease.
    headers = {'x-ms-lease-action': 'break',
               'x-ms-version': '2018-11-09'}
    command = adls_gen2_fs_oauth2_api_client.lease_path(sample_filesystem, sample_directory, headers)
    assert command.response.status_code == 202

    # Release the lease.
    headers = {'x-ms-lease-action': 'release',
               'x-ms-lease-id': lease_id,
               'x-ms-version': '2018-11-09'}
    command = adls_gen2_fs_oauth2_api_client.lease_path(sample_filesystem, sample_directory, headers)
    # logger.info('Release lease response status_code = %d', command.response.status_code)
    assert command.response.status_code == 200


def test_get_path_properties(adls_gen2_fs_oauth2_api_client, sample_filesystem, sample_directory, sample_file):
    # Get path properties for the directory.
    command = adls_gen2_fs_oauth2_api_client.get_path_properties(sample_filesystem, sample_directory)
    headers = command.response.headers
    assert headers['Content-Type'] == 'application/json'
    assert headers['x-ms-resource-type'] == 'directory'

    # Get status for the directory.
    kwargs = {'action': 'getStatus'}
    command = adls_gen2_fs_oauth2_api_client.get_path_properties(sample_filesystem, sample_directory, **kwargs)
    headers = command.response.headers
    assert headers['x-ms-resource-type'] == 'directory'

    # Get path properties for the file.
    path = '{}/{}'.format(sample_directory, sample_file)
    command = adls_gen2_fs_oauth2_api_client.get_path_properties(sample_filesystem, path)
    headers = command.response.headers
    assert headers['Content-Type'] == 'application/json'
    assert headers['x-ms-resource-type'] == 'file'

    # Get status for the file.
    kwargs = {'action': 'getStatus'}
    command = adls_gen2_fs_oauth2_api_client.get_path_properties(sample_filesystem, path, **kwargs)
    headers = command.response.headers
    assert headers['x-ms-resource-type'] == 'file'


def test_file_crud_operations(adls_gen2_fs_oauth2_api_client, sample_filesystem, sample_directory):
    """Test create, read, update and delete on a file."""
    file_name = '{}.txt'.format(get_random_string(string.ascii_lowercase, 6))

    path = '{}/{}'.format(sample_directory, file_name)
    kwargs = {'resource': 'file'}
    headers = {'Content-Length': '0', 'x-ms-version': '2018-11-09'}
    adls_gen2_fs_oauth2_api_client.create_path(sample_filesystem, path, headers=headers, **kwargs)

    try:
        # List path for the directory and verify the contents show the file.
        kwargs = {'directory': sample_directory}
        list_directory_command = adls_gen2_fs_oauth2_api_client.list_path(sample_filesystem, **kwargs)
        paths = list_directory_command.response.json()['paths']
        assert any([item['name'] for item in paths if item['name'] == path])

        # Read file contents and verify the file is empty.
        read_file_contents_command = adls_gen2_fs_oauth2_api_client.read_path(sample_filesystem, path)
        contents = read_file_contents_command.response.content
        assert contents.decode() == ''

        # Append contents.
        first_append_text = MESSI_NAME
        file_contents = _append_text_contents(adls_gen2_fs_oauth2_api_client, sample_filesystem,
                                              path, first_append_text, 0)
        assert file_contents == first_append_text

        # Append more contents.
        second_append_text = RONALDO_NAME
        # Change the position parameter accordingly - we start to append after the last character in file.
        file_contents = _append_text_contents(adls_gen2_fs_oauth2_api_client, sample_filesystem, path,
                                              second_append_text, len(first_append_text))
        assert file_contents == '{}{}'.format(first_append_text, second_append_text)
    finally:
        # Delete file.
        adls_gen2_fs_oauth2_api_client.delete_path(sample_filesystem, path)


# In this method, the assumption is contents type is plain text.
def _append_text_contents(adls_gen2_fs_oauth2_api_client, filesystem, path, contents, append_position):
    contents_length = len(contents)

    # Append contents.
    kwargs = {'action': 'append', 'position': append_position}
    headers = {'Content-Length': str(contents_length), 'Content-Type': 'text/plain'}
    adls_gen2_fs_oauth2_api_client.update_path(filesystem, path, contents, headers, **kwargs)

    # After the append operation, the text sits in an uncommitted buffer on the server.
    # To send buffered data to the file system, flush the contents.
    kwargs = {'action': 'flush', 'position': append_position + contents_length}
    headers = {'Content-Length': '0', 'x-ms-content-type': 'text/plain'}
    adls_gen2_fs_oauth2_api_client.update_path(filesystem, path, headers=headers, **kwargs)

    # Read the contents.
    read_file_contents_command = adls_gen2_fs_oauth2_api_client.read_path(filesystem, path)
    contents = read_file_contents_command.response.content
    return contents.decode()
