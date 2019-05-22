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

# Tests for the filesystem related methods of the API Client.

import base64
import logging
import string
from uuid import uuid4

import pytest

from downstage.utils import get_random_string

logger = logging.getLogger(__name__)
PLAYER_NAME = 'Roger Federer'


def test_login(adls_gen2_fs_oauth2_api_client):
    """Create an instance of ADLS Gen2 api_client and verify login was successful."""
    response = adls_gen2_fs_oauth2_api_client.refresh_oauth2_token_command.response
    expected_auth_header = 'Bearer {}'.format(response.json()['access_token'])
    assert adls_gen2_fs_oauth2_api_client.session.headers['Authorization'] == expected_auth_header


@pytest.mark.parametrize('headers', [None, {'x-ms-client-request-id': str(uuid4())}])
@pytest.mark.parametrize('pass_optional_parameter', [False, True])
def test_create_and_delete_filesystem(adls_gen2_fs_oauth2_api_client, headers, pass_optional_parameter):
    """Create a filesystem and verify with list_filesystem call and later delete and verify again."""
    filesystem_identifier = get_random_string(string.ascii_lowercase, 6)

    kwargs = {'timeout': 30} if pass_optional_parameter else {}
    adls_gen2_fs_oauth2_api_client.create_filesystem(filesystem_identifier, headers=headers, **kwargs)

    response = adls_gen2_fs_oauth2_api_client.list_filesystem(headers, **kwargs)
    filesystems = response['filesystems']
    assert any([item['name'] for item in filesystems if item['name'] == filesystem_identifier])

    adls_gen2_fs_oauth2_api_client.delete_filesystem(filesystem_identifier, headers, **kwargs)

    response = adls_gen2_fs_oauth2_api_client.list_filesystem(headers, **kwargs)
    filesystems = response['filesystems']
    assert not any([item['name'] for item in filesystems if item['name'] == filesystem_identifier])


@pytest.mark.parametrize('headers', [{'x-ms-client-request-id': str(uuid4())}, None])
@pytest.mark.parametrize('pass_optional_parameter', [True, False])
def test_filesystem_get_and_set_properties(adls_gen2_fs_oauth2_api_client, headers, pass_optional_parameter):
    """Create a filesystem, set some propertiees for the same.
    Verify with get_filesystem_properties call."""
    filesystem_identifier = get_random_string(string.ascii_lowercase, 6)
    kwargs = {'timeout': 30} if pass_optional_parameter else {}
    adls_gen2_fs_oauth2_api_client.create_filesystem(filesystem_identifier, headers=headers, **kwargs)

    try:
        adls_gen2_fs_oauth2_api_client.get_filesystem_properties(filesystem_identifier, headers=headers, **kwargs)

        property_to_add = 'player1={}'.format(base64.b64encode(b'Roger Federer').decode())
        if headers:
            headers['x-ms-properties'] = property_to_add
        else:
            headers = {'x-ms-properties': property_to_add}
        adls_gen2_fs_oauth2_api_client.set_filesystem_properties(filesystem_identifier, headers=headers, **kwargs)

        get_properties_command = adls_gen2_fs_oauth2_api_client.get_filesystem_properties(filesystem_identifier,
                                                                                          headers=headers,
                                                                                          **kwargs)
        assert get_properties_command.response.headers['x-ms-properties'] == property_to_add
    finally:
        adls_gen2_fs_oauth2_api_client.delete_filesystem(filesystem_identifier, headers, **kwargs)
