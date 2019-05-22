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

# Tests for the FileSystem object.

import logging
import string

import pytest

from downstage.utils import get_random_string

logger = logging.getLogger(__name__)

FEDERER_NAME = 'Roger Federer'
MESSI_NAME = 'Lionel Messi'
RONALDO_NAME = 'Christiano Ronaldo'


@pytest.fixture(scope="module")
def sample_directory(adls_gen2_fs_oauth2):
    directory_name = get_random_string(string.ascii_lowercase, 6)
    adls_gen2_fs_oauth2.mkdir(directory_name)

    yield directory_name

    adls_gen2_fs_oauth2.rmdir(directory_name)


def test_login(adls_gen2_fs_oauth2):
    """Create an instance of ADLS Gen2 api_client and verify login was successful."""
    response = adls_gen2_fs_oauth2.api_client.refresh_oauth2_token_command.response
    expected_auth_header = 'Bearer {}'.format(response.json()['access_token'])
    assert adls_gen2_fs_oauth2.api_client.session.headers['Authorization'] == expected_auth_header


def test_create_and_delete_directory(adls_gen2_fs_oauth2):
    """Create directory. Later delete the directory."""

    directory_name = get_random_string(string.ascii_lowercase, 6)
    print('1 directory_name =%s', directory_name)
    logger.debug('directory_name =%s', directory_name)
    adls_gen2_fs_oauth2.mkdir(directory_name)

    # Verify directory existence with list_path on the api_client.
    list_directory_command = adls_gen2_fs_oauth2.api_client.list_path(adls_gen2_fs_oauth2.filesystem_id)
    paths = list_directory_command.response.json()['paths']
    assert any([item['name'] for item in paths if item['name'] == directory_name])

    # Delete the directory.
    adls_gen2_fs_oauth2.rmdir(directory_name)

    # Verify directory absence with list_path on the api_client.
    list_directory_command = adls_gen2_fs_oauth2.api_client.list_path(adls_gen2_fs_oauth2.filesystem_id)
    paths = list_directory_command.response.json()['paths']
    assert not any([item['name'] for item in paths if item['name'] == directory_name])


def test_file_crud_operations(adls_gen2_fs_oauth2):
    """Test create, read, update and delete on a file."""
    sample_directory = get_random_string(string.ascii_lowercase, 6)
    adls_gen2_fs_oauth2.mkdir(sample_directory)

    file_name = '{}.txt'.format(get_random_string(string.ascii_lowercase, 6))

    path = '{}/{}'.format(sample_directory, file_name)
    adls_gen2_fs_oauth2.touch(path)

    try:
        # List directory contents and verify created file is listed.
        dl_files_command = adls_gen2_fs_oauth2.ls(sample_directory)
        paths = dl_files_command.response.json()['paths']
        names = [item['name'] for item in paths] if paths else []
        assert any([name for name in names if name == path])

        # Read file contents and verify the file is empty.
        contents = adls_gen2_fs_oauth2.cat(path).response.content.decode()
        assert contents == ''

        # Append contents.
        first_append_text = MESSI_NAME
        adls_gen2_fs_oauth2.write(path, first_append_text)
        file_contents = adls_gen2_fs_oauth2.cat(path).response.content.decode()
        assert file_contents == first_append_text

        # Append more contents.
        second_append_text = RONALDO_NAME
        # Change the position parameter accordingly - we start to append after the last character in file.
        adls_gen2_fs_oauth2.write(path, second_append_text, position=len(first_append_text))
        file_contents = adls_gen2_fs_oauth2.cat(path).response.content.decode()

        # Verify contents using cat.
        assert file_contents == '{}{}'.format(first_append_text, second_append_text)

    finally:
        # Delete file.
        adls_gen2_fs_oauth2.rm(path)

        # List directory contents and verify deleted file is not listed.
        dl_files_command = adls_gen2_fs_oauth2.ls(sample_directory)
        paths = dl_files_command.response.json()['paths']
        names = [item['name'] for item in paths] if paths else []
        assert not any([name for name in names if name == path])
